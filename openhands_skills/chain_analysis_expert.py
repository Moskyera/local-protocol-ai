"""
Chain Analysis Expert Skill for OpenHands
Παρέχει απλοποιημένο, έξυπνο chain analysis για EVM / PulseChain addresses.
Δίνει: από πού έλαβε, πού έστειλε, τι έκανε (interactions, DeFi, contracts), risk flags.
Βασισμένο σε explorer patterns + LLM reasoning + market data integration.
Αυτόματα χρησιμοποιείται από agents για audits, debugging, contract analysis.

Real data: uses free public no-key APIs when on pulsechain:
- BlockScout (api.scan.pulsechain.com/api  Etherscan-compatible tokentx)
- PulseX subgraph (graph.pulsechain.com .../pulsex) for swaps
- Public RPC (rpc.pulsechain.com) eth_getLogs for Transfer events + eth_call for symbols
Optional premium (if you provide free Moralis key in .env as MORALIS_API_KEY):
- Wallet History endpoint → categorized transfers (token_swap, receive, send) with excellent decoding.
Everything is optional + has strong public free fallbacks. No key = still fully functional.

USD risk tiers (exact user spec, hardened in upgrade):
- Big native PLS receive is ALWAYS valued in USD (not raw coin count). Real value threshold starts ~$50k+ for "very large".
- Tiers: >50000 very large (+45 risk), >10000 large (+30), >1000 medium (+15), >100 small (+5).
- Tiny amounts ($50 / $100 / $500) add almost zero risk score. Pattern "big PLS receive + low activity + meme bag" ONLY triggers on real USD thresholds + low nonce + meme bag.
- This is the Blockchain Intelligence specialist's core contract.
"""

import os
import re
import sys
from datetime import datetime, timezone

# Make the skills package importable when OpenHands runs it in /workspace or isolated env
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Defensive imports for OpenHands sandbox (where outer market-agent modules may not exist)
try:
    from logger import log
except Exception:
    class _Log:
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
    log = _Log()

try:
    from openhands_skills.tool_integration_hub import tool_hub
except Exception:
    class _DummyToolHub:
        def run_market_snapshot(self):
            return "Market snapshot not available (OpenHands sandbox mode). Using on-chain USD values from Moralis/public explorers."
        def run_master_report(self, *a, **k):
            return "Master market report not available in this environment."
    tool_hub = _DummyToolHub()

try:
    from openhands_skills.persistent_memory import persistent_memory
except Exception:
    class _DummyMemory:
        def store(self, *a, **k): pass
        def retrieve(self, *a, **k): return []
    persistent_memory = _DummyMemory()

try:
    import requests
except ImportError:
    requests = None

# For parallel public API fallbacks (directly reduces first-call latency on domain tools)
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional Moralis (user-provided free key for enhanced PulseChain data)
# Put in .env: MORALIS_API_KEY=yourkey
# When present → used first for rich categorized wallet history (token_swap etc.)
# Always falls back to pure free public APIs (BlockScout / PulseX subgraph / RPC)
try:
    from config import config as app_config
    MORALIS_API_KEY = getattr(app_config, "MORALIS_API_KEY", "") or os.getenv("MORALIS_API_KEY", "")
except Exception:
    MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")

#: Measured, not guessed: the constants that used to live here were HEX
#: 0.000012 against a live 0.003151 — understated 263x — and PLSX 12.6x. They
#: did not merely mislabel a transfer. They GATED it: at a $5,000 threshold a
#: HEX move had to be 416,666,667 HEX to be flagged, which is $1.31M of real
#: value, so every genuine whale move between $5k and $1.31M was valued below
#: threshold and silently dropped. Labelling the estimate was not enough — a
#: wrong number that decides visibility has to stop deciding.
#:
#: Prices are now resolved live, once per process, and a symbol with no live
#: price is reported as UNPRICED rather than valued from a constant.
_PRICE_CACHE = {}
STATIC_PRICES_NOTE = ("δεν βρέθηκε ζωντανή τιμή — η μεταφορά αναφέρεται "
                      "χωρίς αποτίμηση, ΟΧΙ ως μικρή")


#: dexscreener chain ids for the chains this expert analyses.
_CHAIN_IDS = {"pulsechain": "pulsechain", "ethereum": "ethereum"}


def live_price(symbol: str, chain: str = "pulsechain", timeout: float = 6.0):
    """Live USD price for a token ON THE GIVEN CHAIN, or None.

    The chain filter is not a nicety. A bare symbol search returns the highest
    liquidity pair on ANY chain, and HEX exists on both Ethereum and PulseChain
    at very different prices — measured during this work, $0.01232 unfiltered
    versus a PulseChain figure an order of magnitude apart. Replacing a stale
    constant with confidently-wrong live data would have been no improvement.

    None means UNKNOWN, and every caller must treat it as unknown rather than as
    zero. Zero is what made large transfers disappear from the alerts.
    """
    sym = (symbol or "").upper()
    want = _CHAIN_IDS.get((chain or "").lower(), (chain or "").lower())
    key = (sym, want)
    if key in _PRICE_CACHE:
        return _PRICE_CACHE[key]
    price = None
    try:
        import json as _json
        import urllib.request
        url = f"https://api.dexscreener.com/latest/dex/search?q={sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "mosky/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            pairs = _json.loads(r.read()).get("pairs") or []
        best = None
        for pr in pairs:
            if (pr.get("chainId", "").lower() != want
                    or pr.get("baseToken", {}).get("symbol", "").upper() != sym
                    or not pr.get("priceUsd")):
                continue
            liq = float((pr.get("liquidity") or {}).get("usd") or 0)
            if best is None or liq > best[0]:
                best = (liq, float(pr["priceUsd"]))
        price = best[1] if best else None
    except Exception:
        price = None
    _PRICE_CACHE[key] = price
    return price

class ChainAnalysisExpert:
    def __init__(self):
        self.known_patterns = {
            "ethereum": {
                "cex": ["0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be", "0x28c6c06298d514db089934071355e5743bf21d60"],  # Binance examples
                "dex": ["0x7a250d5630b4cf539739df2c5dacb4c659f2488d"],  # Uniswap V2 router
                "explorer_base": "https://etherscan.io/address/"
            },
            "pulsechain": {
                "cex": [],  # Add known if any
                "dex": ["0x98bf93ebf5c380C0e6Ae8e192A7e2AE08edAcc02"],  # PulseX router (v1)
                "explorer_base": "https://scan.pulsechain.com/address/"
            }
        }

        # Free public APIs (no key required)
        self.blockscout_api = "https://api.scan.pulsechain.com/api"
        self.pulsex_graphql = "https://graph.pulsechain.com/subgraphs/name/pulsechain/pulsex"
        self.public_rpcs = {
            "pulsechain": "https://rpc.pulsechain.com",
            "ethereum": "https://eth.llamarpc.com"
        }
        self._token_cache = {}  # per-run cache for symbol/decimals from RPC calls

        # Ecosystem tokens on Pulsechain for large movement scanning/alerts (HEX, PLSX, INC etc.)
        # Update contracts as needed; used for symbol-based or contract-specific queries.
        self.ecosystem_tokens = {
            "pulsechain": {
                "HEX": "0x57fde0a71132198bbec939b98976993d8d89d225",
                "PLSX": "0x95b303987a60c132dedb7d58c442c4a9a9f4e4f0",  # PulseX token
                "INC": "0x4f9a0e7fd2bf6067db6994cf12e4495df938e6e9",  # example INC; replace with accurate
            }
        }

        # Expanded known exploit / suspicious patterns (function signatures, common vulnerable contracts, etc.)
        self.exploit_patterns = [
            "reentrancy", "selfdestruct", "delegatecall", "tx.origin", "unchecked call", 
            "flash loan attack", "oracle manipulation", "rug pull", "drain", "phishing",
            "0x23b872dd",  # transferFrom signature often in exploits
            "0xa9059cbb",  # transfer
            "known exploit contract", "mixer", "tornado cash"
        ]

        # PulseX router for swap detection
        self.pulsex_router = self.known_patterns["pulsechain"]["dex"][0].lower()

        # Optional Moralis key (if provided in .env, we get much richer categorized wallet history)
        self.moralis_key = MORALIS_API_KEY
        self.moralis_base = "https://deep-index.moralis.io/api/v2.2"

    # ---------- FREE PUBLIC API FETCHERS (PulseChain / PulseX) ----------

    def _decode_string(self, hex_data: str) -> str:
        if not hex_data or hex_data == "0x":
            return ""
        h = hex_data[2:] if hex_data.startswith("0x") else hex_data
        try:
            if len(h) < 128:
                return ""
            strlen = int(h[64:128], 16)
            data_start = 128
            end = data_start + strlen * 2
            raw = bytes.fromhex(h[data_start:end])
            return raw.decode("utf-8", errors="replace").strip("\x00").strip()
        except Exception:
            return ""

    def _decode_uint(self, hex_data: str) -> int:
        if not hex_data or hex_data == "0x":
            return 18
        h = hex_data[2:] if hex_data.startswith("0x") else hex_data
        try:
            return int(h, 16)
        except Exception:
            return 18

    def _get_token_meta(self, token_address: str, rpc_url: str) -> dict:
        token = token_address.lower()
        if token in self._token_cache:
            return self._token_cache[token]
        meta = {"symbol": token[-6:].upper(), "decimals": 18, "name": ""}
        if not requests:
            self._token_cache[token] = meta
            return meta
        # symbol()
        try:
            body = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": token, "data": "0x95d89b41"}, "latest"],
                "id": 1
            }
            r = requests.post(rpc_url, json=body, timeout=6)
            res = r.json().get("result", "0x")
            sym = self._decode_string(res)
            if sym:
                meta["symbol"] = sym[:20]
        except Exception:
            pass
        # decimals()
        try:
            body = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": token, "data": "0x313ce567"}, "latest"],
                "id": 1
            }
            r = requests.post(rpc_url, json=body, timeout=6)
            res = r.json().get("result", "0x")
            dec = self._decode_uint(res)
            if dec > 0:
                meta["decimals"] = min(dec, 36)
        except Exception:
            pass
        self._token_cache[token] = meta
        return meta

    def _fetch_token_transfers_blockscout(self, address: str, chain: str = "pulsechain", limit: int = 50) -> list:
        """Free public BlockScout API (Etherscan compatible) - best for token transfers with symbols."""
        if chain != "pulsechain" or not requests:
            return []
        try:
            params = {
                "module": "account",
                "action": "tokentx",
                "address": address,
                "sort": "desc",
                "offset": str(min(limit, 100))
            }
            resp = requests.get(self.blockscout_api, params=params, timeout=12, headers={"User-Agent": "GrokChainAgent/1.0"})
            if resp.status_code != 200:
                return []
            data = resp.json()
            if str(data.get("status")) != "1" or not isinstance(data.get("result"), list):
                return []
            out = []
            for tx in data["result"][:limit]:
                try:
                    dec = int(tx.get("tokenDecimal") or 18)
                    raw = int(tx.get("value") or 0)
                    human = raw / (10 ** dec) if dec else raw
                    ts = int(tx.get("timeStamp") or 0)
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else ""
                    out.append({
                        "timestamp": str(ts),
                        "datetime": dt,
                        "tx_hash": tx.get("hash", ""),
                        "from": tx.get("from", "").lower(),
                        "to": tx.get("to", "").lower(),
                        "token_address": tx.get("contractAddress", "").lower(),
                        "symbol": tx.get("tokenSymbol", "???"),
                        "name": tx.get("tokenName", ""),
                        "value_raw": str(raw),
                        "value": round(human, 8),
                        "decimals": dec,
                        "block": tx.get("blockNumber"),
                    })
                except Exception:
                    continue
            return out
        except Exception as e:
            log.warning(f"BlockScout tokentx failed (free API): {e}")
            return []

    def _fetch_token_transfers_for_contract(self, contract_address: str, chain: str = "pulsechain", limit: int = 50) -> list:
        """Fetch tokentx for a specific token contract (to find its movements/transfers on the chain).
        Uses BlockScout with contractaddress param to get recent transfers of that token.
        This enables scanning without a target wallet address.
        """
        url = f"{self.blockscout_api}/api"
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract_address,
            "sort": "desc",
            "offset": str(limit),
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "1":
                return []
            txs = data.get("result", []) or []
            out = []
            for tx in txs:
                try:
                    dec = int(tx.get("tokenDecimal") or 18)
                    raw = int(tx.get("value") or 0)
                    human = raw / (10 ** dec) if dec else raw
                    ts = int(tx.get("timeStamp") or 0)
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else ""
                    out.append({
                        "timestamp": str(ts),
                        "datetime": dt,
                        "tx_hash": tx.get("hash", ""),
                        "from": tx.get("from", "").lower(),
                        "to": tx.get("to", "").lower(),
                        "token_address": tx.get("contractAddress", "").lower(),
                        "symbol": tx.get("tokenSymbol", "???"),
                        "name": tx.get("tokenName", ""),
                        "value_raw": str(raw),
                        "value": round(human, 8),
                        "decimals": dec,
                        "block": tx.get("blockNumber"),
                    })
                except Exception:
                    continue
            return out
        except Exception as e:
            log.warning(f"BlockScout token contract tx failed: {e}")
            return []

    def _fetch_pulsex_swaps_graphql(self, address: str, limit: int = 30) -> list:
        """Free public PulseX (Uniswap-fork) subgraph - excellent for real buy/sell via DEX."""
        if not requests:
            return []
        q = """
        query($user: String!) {
          swaps(first: %d, orderBy: timestamp, orderDirection: desc, where: { from: $user }) {
            id
            timestamp
            from
            to
            amount0In
            amount0Out
            amount1In
            amount1Out
            pair {
              token0 { id symbol }
              token1 { id symbol }
            }
          }
        }
        """ % min(limit, 50)
        try:
            resp = requests.post(
                self.pulsex_graphql,
                json={"query": q, "variables": {"user": address.lower()}},
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            j = resp.json()
            swaps = (j.get("data") or {}).get("swaps") or []
            return swaps
        except Exception as e:
            log.warning(f"PulseX subgraph query failed (free): {e}")
            return []

    def _fetch_transfers_via_rpc_logs(self, address: str, chain: str = "pulsechain", max_logs: int = 50) -> list:
        """Fallback free data via public RPC eth_getLogs (Transfer events). Less pretty but real on-chain data."""
        rpc = self.public_rpcs.get(chain, self.public_rpcs["pulsechain"])
        if not requests:
            return []
        sig = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        padded = "0x" + "0" * 24 + address[2:].lower()
        # Recent-ish range (public nodes often limit wide ranges)
        from_block = "0x0"
        out = []
        for is_in, t1, t2 in [(True, None, padded), (False, padded, None)]:
            try:
                params = [{
                    "fromBlock": from_block,
                    "toBlock": "latest",
                    "topics": [sig, t1, t2]
                }]
                body = {"jsonrpc": "2.0", "method": "eth_getLogs", "params": params, "id": 1}
                r = requests.post(rpc, json=body, timeout=15)
                j = r.json()
                if j.get("error"):
                    continue
                for l in (j.get("result") or [])[:max_logs]:
                    try:
                        token = l.get("address", "").lower()
                        meta = self._get_token_meta(token, rpc)
                        val_raw = int(l.get("data", "0x0"), 16)
                        dec = meta.get("decimals", 18)
                        human = val_raw / (10 ** dec) if dec else val_raw
                        topics = l.get("topics", [])
                        fr = ("0x" + topics[1][-40:]) if len(topics) > 1 else ""
                        to = ("0x" + topics[2][-40:]) if len(topics) > 2 else ""
                        out.append({
                            "timestamp": l.get("blockNumber"),
                            "datetime": f"block {l.get('blockNumber')}",
                            "tx_hash": l.get("transactionHash", ""),
                            "from": fr.lower(),
                            "to": to.lower(),
                            "token_address": token,
                            "symbol": meta.get("symbol", "???"),
                            "value_raw": str(val_raw),
                            "value": round(human, 8),
                            "decimals": dec,
                            "block": l.get("blockNumber"),
                            "via_rpc": True,
                        })
                    except Exception:
                        continue
            except Exception:
                continue
        # dedup by tx+token rough
        seen = set()
        deduped = []
        for item in out:
            key = (item.get("tx_hash"), item.get("token_address"))
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped[:max_logs]

    def _fetch_moralis_wallet_history(self, address: str, chain: str = "pulsechain", limit: int = 50) -> list:
        """Optional but excellent: Use Moralis Wallet History (free tier key).
        Gives categorized, decoded activity (token_swap, token_receive, token_send, approve, contract_interaction etc)
        + native_transfers + erc20_transfers. This is the richest source when key is present.
        """
        if not self.moralis_key or not requests:
            return []
        moralis_chain = "pulse" if chain.lower() == "pulsechain" else "eth"
        url = f"{self.moralis_base}/wallets/{address}/history"
        params = {
            "chain": moralis_chain,
            "order": "DESC",
            "limit": str(min(limit, 100))
        }
        headers = {
            "accept": "application/json",
            "X-API-Key": self.moralis_key
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                if resp.status_code == 401:
                    log.warning("Moralis 401 Unauthorized - key invalid/expired or insufficient plan for /wallets/history on this chain. Using public fallbacks only. Verify MORALIS_API_KEY and PulseChain support at moralis.io.")
                else:
                    log.warning(f"Moralis history non-200: {resp.status_code}")
                return []
            data = resp.json()
            results = data.get("result", []) or []
            return results
        except Exception as e:
            log.warning(f"Moralis fetch failed: {e}")
            return []

    def _fetch_moralis_balances(self, address: str, chain: str = "pulsechain") -> list:
        """Moralis current token holdings + USD values (very useful for portfolio context)."""
        if not self.moralis_key or not requests:
            return []
        moralis_chain = "pulse" if chain.lower() == "pulsechain" else "eth"
        url = f"{self.moralis_base}/wallets/{address}/tokens"
        params = {"chain": moralis_chain, "limit": "50"}
        headers = {"accept": "application/json", "X-API-Key": self.moralis_key}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=12)
            if resp.status_code != 200:
                return []
            return resp.json().get("result", []) or []
        except Exception:
            return []

    def fetch_real_token_activity(self, address: str, chain: str = "pulsechain", limit: int = 40) -> dict:
        """Primary real-data fetcher.
        Tries: Moralis (if key) for rich categorized history + portfolio > BlockScout > PulseX subgraph > RPC logs.
        Now returns much more than transfers: native PLS flows, categories, approvals, current balances (when Moralis available).
        Always has free public fallbacks. No key required for basic functionality.
        """
        address = (address or "").lower().strip()
        if not address.startswith("0x") or len(address) != 42:
            return {"address": address, "chain": chain, "source": "invalid", "transfers": [], "dex_swaps": [], "bought": [], "sold": [], "errors": ["bad address"]}
        activity = {
            "address": address,
            "chain": chain,
            "source": "none",
            "transfers": [],
            "native_transfers": [],
            "dex_swaps": [],
            "bought": [],
            "sold": [],
            "categories": {},
            "approvals": [],
            "current_balances": [],
            "approx_usd_value": 0.0,
            "errors": []
        }

        # === Premium source (if free Moralis key provided): Wallet History with categories ===
        moralis_used = False
        if chain == "pulsechain":
            try:
                moralis_items = self._fetch_moralis_wallet_history(address, chain, limit)
                if moralis_items:
                    moralis_transfers = []
                    native_list = []
                    cat_count = {}
                    approvals = []

                    for item in moralis_items:
                        ts = item.get("block_timestamp") or item.get("timestamp")
                        category = (item.get("category") or "unknown").lower()
                        cat_count[category] = cat_count.get(category, 0) + 1
                        tx_hash = item.get("hash") or item.get("transaction_hash", "")
                        short_tx = tx_hash[:10] + "..." if tx_hash else ""

                        # Native PLS movements (very important - big receives etc.)
                        for n in item.get("native_transfers", []):
                            try:
                                val_wei = int(n.get("value", 0) or 0)
                                val = val_wei / 1e18
                                fr = n.get("from_address", "").lower()
                                to = n.get("to_address", "").lower()
                                native_list.append({
                                    "timestamp": str(ts)[:19] if ts else "",
                                    "datetime": str(ts)[:16] if ts else "",
                                    "tx_hash": tx_hash,
                                    "from": fr,
                                    "to": to,
                                    "value": round(val, 6),
                                    "symbol": "PLS",
                                    "category": category,
                                })
                            except:
                                continue

                        # ERC20
                        for t in item.get("erc20_transfers", []):
                            try:
                                sym = t.get("token_symbol") or t.get("symbol") or "TOK"
                                token_addr = (t.get("address") or t.get("token_address") or "").lower()
                                # Proper value_decimal handling (Moralis usually gives the human readable decimal-adjusted value)
                                val_decimal = t.get("value_decimal")
                                if val_decimal is not None:
                                    try:
                                        val = float(val_decimal)
                                    except:
                                        val = 0.0
                                else:
                                    raw = int(t.get("value") or 0)
                                    dec = int(t.get("token_decimals") or 18)
                                    val = raw / (10 ** dec) if dec > 0 else raw
                                val = round(val, 8) if val < 1e6 else round(val, 4)  # sensible display for high supply tokens
                                fr = (t.get("from_address") or "").lower()
                                to = (t.get("to_address") or "").lower()
                                moralis_transfers.append({
                                    "timestamp": str(ts)[:19] if ts else "",
                                    "datetime": str(ts)[:16] if ts else "",
                                    "tx_hash": tx_hash,
                                    "from": fr,
                                    "to": to,
                                    "token_address": token_addr,
                                    "symbol": sym,
                                    "value": round(val, 8),
                                    "value_raw": str(t.get("value", "")),
                                    "decimals": int(t.get("token_decimals") or 18),
                                    "category": category,
                                    "via_moralis": True,
                                })
                            except:
                                continue

                        # Approves (common before DeFi)
                        if "approve" in category:
                            approvals.append({"tx": tx_hash, "ts": str(ts)[:16], "category": category})

                    if moralis_transfers or native_list:
                        activity["transfers"].extend(moralis_transfers)
                        activity["native_transfers"].extend(native_list)
                        activity["categories"] = cat_count
                        activity["approvals"] = approvals
                        activity["source"] = "moralis"
                        moralis_used = True
            except Exception as e:
                activity["errors"].append(f"moralis:{str(e)[:80]}")

            # Current portfolio snapshot from Moralis (great for tokenomics context)
            try:
                bals = self._fetch_moralis_balances(address, chain)
                if bals:
                    activity["current_balances"] = [
                        {
                            "symbol": b.get("symbol"),
                            "balance": b.get("balance_formatted"),
                            "usd": round(float(b.get("usd_value", 0) or 0), 2),
                            "token_address": b.get("token_address", "").lower()
                        } for b in bals[:20]
                    ]
                    activity["approx_usd_value"] = round(sum(float(b.get("usd_value", 0) or 0) for b in bals), 2)
            except Exception as e:
                activity["errors"].append(f"moralis_balances:{str(e)[:60]}")

        # === Public free fallbacks in PARALLEL (BlockScout + PulseX GraphQL + RPC logs) ===
        # Direct attack on the main latency complaint (first calls were 30-45s+). All three sources are independent.
        # We still respect the original sequential logic for merging, but fetch concurrently.
        def _bs_job():
            if not moralis_used:
                try:
                    return ("bs", self._fetch_token_transfers_blockscout(address, chain, limit))
                except Exception as e:
                    activity["errors"].append(f"blockscout:{str(e)[:80]}")
                    return ("bs", [])
            return ("bs", [])

        def _px_job():
            if chain == "pulsechain":
                try:
                    return ("px", self._fetch_pulsex_swaps_graphql(address, min(limit, 30)))
                except Exception as e:
                    activity["errors"].append(f"pulsex_gql:{str(e)[:80]}")
                    return ("px", [])
            return ("px", [])

        def _rpc_job():
            if len(activity.get("transfers", [])) < 5:
                try:
                    return ("rpc", self._fetch_transfers_via_rpc_logs(address, chain, limit))
                except Exception as e:
                    activity["errors"].append(f"rpc_logs:{str(e)[:80]}")
                    return ("rpc", [])
            return ("rpc", [])

        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(_bs_job), ex.submit(_px_job), ex.submit(_rpc_job)]
            for fut in as_completed(futs, timeout=22):
                try:
                    kind, data = fut.result()
                    if kind == "bs" and data:
                        activity["transfers"] = data
                        activity["source"] = "blockscout"
                    elif kind == "px" and data:
                        activity["dex_swaps"] = data
                        src = activity.get("source", "none")
                        if "moralis" in src:
                            if "+pulsex_subgraph" not in src:
                                activity["source"] = src + "+pulsex_subgraph"
                        elif src in ("none", "blockscout"):
                            base = "moralis" if moralis_used else src
                            activity["source"] = base + ("+pulsex_subgraph" if src != "none" else "pulsex_subgraph")
                    elif kind == "rpc" and data:
                        have_hashes = {t.get("tx_hash") for t in activity.get("transfers", [])}
                        for t in data:
                            if t.get("tx_hash") not in have_hashes:
                                activity["transfers"].append(t)
                        src = activity.get("source", "")
                        if "rpc" not in src:
                            activity["source"] = (src + "+rpc_logs").strip("+")
                except Exception as e:
                    # one source timed out or crashed; others may have succeeded
                    log.warning(f"Parallel public fetch partial failure: {e}")

        # On-chain activity metrics for risk scoring (low activity detection - key for "low activity" pattern)
        try:
            rpc = self.public_rpcs.get(chain, self.public_rpcs["pulsechain"])
            nonce_body = {"jsonrpc":"2.0", "method":"eth_getTransactionCount", "params":[address, "latest"], "id":1}
            r = requests.post(rpc, json=nonce_body, timeout=5)
            nonce = int(r.json().get("result", "0x0"), 16)
            activity["onchain_nonce"] = nonce
            activity["activity_level"] = "very_low" if nonce < 10 else ("low" if nonce < 50 else "medium")
        except:
            activity["onchain_nonce"] = None
            activity["activity_level"] = "unknown"

        # Clean source string
        src = activity.get("source", "none")
        if src.startswith("none+"):
            src = src[5:]
        activity["source"] = src or "public_fallbacks"

        # Build buy/sell lists (improved with Moralis categories + native awareness)
        buys = []
        sells = []
        router = self.pulsex_router
        for t in activity["transfers"]:
            try:
                sym = t.get("symbol") or "TOK"
                val = t.get("value", 0)
                dt = (t.get("datetime") or str(t.get("timestamp", "")))[:16]
                short_tx = (t.get("tx_hash") or "")[:10] + "..."
                via_dex = router in (t.get("from", "") + t.get("to", "")).lower()
                cat = (t.get("category") or "").lower()

                # Use Moralis category when present (very accurate)
                is_buy = any(x in cat for x in ["receive", "swap", "mint", "airdrop"]) if cat else False
                is_sell = any(x in cat for x in ["send", "burn"]) if cat else False

                if t.get("to", "") == address or is_buy:
                    tag = " (PulseX swap in)" if via_dex or "swap" in cat else ""
                    prefix = "Bought (swap)" if "swap" in cat else "Bought/Received"
                    if val > 0.000001:  # filter dust
                        buys.append(f"{prefix} {val} {sym} on {dt}{tag} tx:{short_tx}")
                elif t.get("from", "") == address or is_sell:
                    tag = " (PulseX swap out)" if via_dex or "swap" in cat else ""
                    prefix = "Sold (swap)" if "swap" in cat else "Sold/Sent"
                    if val > 0.000001:
                        sells.append(f"{prefix} {val} {sym} on {dt}{tag} tx:{short_tx}")
            except Exception:
                continue

        # Also surface big native PLS receives/sends (very relevant on PulseChain)
        for n in activity.get("native_transfers", []):
            try:
                val = n.get("value", 0)
                if val > 100:  # only report meaningful PLS amounts
                    dt = n.get("datetime", "")
                    short = n.get("tx_hash", "")[:10] + "..."
                    if n.get("to") == address:
                        buys.append(f"Received {val:,.2f} PLS (native) on {dt} tx:{short}")
                    else:
                        sells.append(f"Sent {val:,.2f} PLS (native) on {dt} tx:{short}")
            except:
                pass

        # Add DEX swap details (more accurate direction for AMM)
        for s in activity["dex_swaps"]:
            try:
                ts = int(s.get("timestamp") or 0)
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "recent"
                p = s.get("pair") or {}
                t0 = (p.get("token0") or {}).get("symbol", "?")
                t1 = (p.get("token1") or {}).get("symbol", "?")
                a0in = float(s.get("amount0In") or 0)
                a0out = float(s.get("amount0Out") or 0)
                a1in = float(s.get("amount1In") or 0)
                a1out = float(s.get("amount1Out") or 0)
                short = (s.get("id") or "")[:10] + "..."
                if a0in > 0:
                    sells.append(f"Sold ~{a0in:.4f} {t0} -> bought {t1} on {dt} (PulseX) id:{short}")
                if a1in > 0:
                    # received t1 by giving t0? adjust based on outs
                    buys.append(f"Bought ~{a1out or a1in:.4f} {t1} on {dt} (PulseX) id:{short}")
                if a0out > 0 and a1in == 0:
                    buys.append(f"Bought ~{a0out:.4f} {t0} on {dt} (PulseX) id:{short}")
            except Exception:
                continue

        activity["bought"] = buys[:15]
        activity["sold"] = sells[:15]

        # === Large ecosystem token movement alerts (new for HEX, PLSX, INC on Pulsechain) ===
        # Detects big transfers of key Pulsechain ecosystem tokens using same USD-value philosophy as native PLS.
        # "Large" default: > $5,000 USD (tunable via context or future param). Small moves ignored per your rules.
        # This provides "alerts" as structured data in wallet analysis (usable by supervisor/MCP agent in chat).
        # No Telegram/briefing touch — alerts surface in the agent's structured output / OpenHands chat.
        ECOSYSTEM_TOKENS = {"HEX", "PLSX", "INC"}
        # Last-resort prices, used ONLY when no API supplied one. These are
        # constants in a source file and go stale the day they are written; an
        # audit found the HEX figure off by a factor of hundreds. They are kept
        # because a rough magnitude beats nothing, but every value derived from
        # them is labelled static_estimate so it can never be read as a quote.
        unpriced_moves = []
        DEFAULT_LARGE_USD = 5000.0  # conservative start; user can specify higher in context (e.g. 10000, 50000)
        large_ecosystem = []
        all_transfers = activity.get("transfers", []) + activity.get("native_transfers", [])
        for t in all_transfers:
            sym = (t.get("symbol") or "").upper()
            if sym in ECOSYSTEM_TOKENS:
                val = t.get("value", 0) or 0
                # Prefer usd_value if Moralis provided it; fallback to on-chain approx using price map (generalized from research on last30d patterns for valuation without premium APIs)
                usd_val = t.get("usd_value") or t.get("usd") or 0.0
                try:
                    usd_val = float(usd_val)
                except:
                    usd_val = 0.0
                usd_source = "api" if usd_val else ""
                if usd_val == 0:
                    # A HARDCODED price is not market data. It was silently
                    # multiplied into a USD figure that then decided whether an
                    # alert fired at all — so a stale constant does not just
                    # mislabel a transfer, it makes the transfer DISAPPEAR by
                    # dropping it under the threshold. The value is still useful
                    # as a rough estimate; it must simply never pass for a quote.
                    px = live_price(sym, chain)
                    usd_val = val * px if px else 0
                    usd_source = "live" if px else "unpriced"

                if usd_source == "unpriced":
                    # No price from anywhere. Previously usd_val stayed 0, the
                    # threshold test failed, and a large transfer vanished with
                    # no trace. Surface it by TOKEN amount instead.
                    unpriced_moves.append({
                        "symbol": sym,
                        "token_value": round(val, 6) if val < 1e6 else round(val, 2),
                        "tx_hash": t.get("tx_hash", ""),
                        "timestamp": t.get("timestamp", ""),
                        "note": f"{sym}: δεν υπάρχει τιμή — δεν μπορεί να "
                                f"αποτιμηθεί σε USD, δεν κρίθηκε ως μεγάλη ή μικρή",
                    })
                    continue

                if usd_val >= DEFAULT_LARGE_USD:
                    large_ecosystem.append({
                        "symbol": sym,
                        "usd_value": round(usd_val, 2),
                        "token_value": round(val, 6) if val < 1e6 else round(val, 2),
                        "tx_hash": t.get("tx_hash", ""),
                        "from": t.get("from", ""),
                        "to": t.get("to", ""),
                        "timestamp": t.get("timestamp", ""),
                        "category": t.get("category", ""),
                        "usd_source": usd_source,
                        "alert": (f"LARGE {sym} movement ≈ ${usd_val:,.0f} USD"
                                  + ("" if usd_source == "live"
                                     else " (ΧΩΡΙΣ ΑΠΟΤΙΜΗΣΗ)"))
                    })
        activity["large_ecosystem_movements"] = large_ecosystem
        if large_ecosystem:
            activity["ecosystem_alerts"] = [m["alert"] for m in large_ecosystem]
        if unpriced_moves:
            # Never silently dropped again.
            activity["unpriced_ecosystem_movements"] = unpriced_moves
            activity["unpriced_note"] = (
                f"{len(unpriced_moves)} μεταφορές δεν αποτιμήθηκαν — "
                f"δεν βρέθηκε τιμή. Δεν σημαίνει ότι ήταν μικρές.")
        if any(m.get("usd_source") != "live" for m in large_ecosystem):
            activity["ecosystem_price_warning"] = STATIC_PRICES_NOTE

        # Clean source
        src = activity.get("source", "none")
        if src.startswith("none+"):
            src = src[5:]
        activity["source"] = src or "public_fallbacks"

        # === PnL estimate with market data + Risk scoring (added before run_task exposure) ===
        try:
            activity["pnl_estimate"] = self._estimate_pnl_with_market(activity, chain)
        except Exception as e:
            activity["pnl_estimate"] = {"error": str(e)[:80], "note": "PnL estimation skipped"}
        try:
            activity["risk_score"] = self._calculate_risk_score(activity, chain)
        except Exception as e:
            activity["risk_score"] = {"error": str(e)[:80]}

        return activity

    def get_real_buy_sell_history(self, address: str, chain: str = "pulsechain") -> dict:
        """Returns real fetched buy/sell data (preferred) + manual steps as fallback."""
        activity = self.fetch_real_token_activity(address, chain)
        steps = self.get_real_buy_sell_history_guidance(address, chain)
        summary = []
        if activity.get("bought"):
            summary.append("=== FETCHED VIA FREE APIs (BlockScout / PulseX Subgraph / RPC) ===")
            summary += [f"IN:  {b}" for b in activity["bought"][:8]]
        if activity.get("sold"):
            summary += [f"OUT: {s}" for s in activity["sold"][:8]]
        if not activity.get("bought") and not activity.get("sold"):
            summary = ["No recent token transfers or PulseX swaps found via free public APIs (may be new/low activity wallet or temp API hiccup)."]
        return {
            "fetched": activity,
            "manual_fallback_steps": steps,
            "summary": summary,
            "has_real_data": bool(activity.get("bought") or activity.get("sold") or activity.get("transfers"))
        }

    def scan_large_ecosystem_movements(self, tokens=None, min_usd=5000, limit=20):
        """Scan Pulsechain for recent large movements of specific ecosystem tokens (HEX, PLSX, INC etc.)
        WITHOUT requiring a target wallet address.
        Returns list of large transfers (from/to addresses, tx, USD approx value).
        This enables queries like "large HEX PLSX INC moves on pulsechain" and then start analysis on the returned addresses.
        Uses BlockScout per-token-contract tokentx + basic USD (improve with on-chain price once the guarded proposal is applied).
        Small moves below min_usd are ignored per your rules.
        """
        if tokens is None:
            tokens = ["HEX", "PLSX", "INC"]
        chain = "pulsechain"
        contracts = self.ecosystem_tokens.get(chain, {})
        all_large = []
        for sym in tokens:
            contract = contracts.get(sym.upper())
            if not contract:
                continue
            unpriced_large = []
            txs = self._fetch_token_transfers_for_contract(contract, chain, limit * 2)
            for tx in txs:
                val = tx.get("value", 0)
                # Basic USD approx (update with real prices or the on-chain estimator from the improvement proposal).
                # For now, rough prices; in practice use market snapshot or the _estimate helper.
                # Second copy of the same defect as in the wallet path: a
                # constant written into the source, multiplied into USD, and
                # then used as the threshold test — so a stale number does not
                # mislabel a transfer, it deletes it.
                price = live_price(sym, chain) or 0
                usd = val * price
                if not price:
                    unpriced_large.append({
                        "symbol": sym,
                        "token_value": round(val, 8),
                        "tx_hash": tx.get("tx_hash", ""),
                        "note": f"{sym}: καμία τιμή — δεν αποτιμήθηκε",
                    })
                    continue
                if usd >= min_usd:
                    all_large.append({
                        "symbol": sym,
                        "usd_value": round(usd, 2),
                        "token_value": round(val, 8),
                        "tx_hash": tx.get("tx_hash", ""),
                        "from": tx.get("from", ""),
                        "to": tx.get("to", ""),
                        "timestamp": tx.get("timestamp", ""),
                        "alert": f"LARGE {sym} movement ≈ ${usd:,.0f} USD on Pulsechain"
                    })
        all_large.sort(key=lambda x: -x.get("usd_value", 0))
        return all_large[:limit]

    def analyze_address(self, address: str, chain: str = "ethereum", context: str = "") -> dict:
        """
        Κύρια συνάρτηση: Δίνει structured chain analysis.
        Input: address + chain (ethereum/pulsechain) + optional context (π.χ. από contract audit).
        Output: dict με incoming, outgoing, actions, risks, explorer links, recommendations.
        """
        log.info(f"Chain Analysis Expert: Analyzing {address} on {chain}")
        
        chain = chain.lower()
        if chain not in ["ethereum", "pulsechain"]:
            chain = "ethereum"
        
        explorer_base = self.known_patterns[chain]["explorer_base"]
        explorer_link = f"{explorer_base}{address}"
        
        lower_context = (context or "").lower()
        known = self.known_patterns[chain]
        
        # Basic classification - corrected: respect user saying it's a wallet (EOA)
        is_likely_contract = "contract" in lower_context or "deploy" in lower_context or "proxy" in lower_context
        address_type = "Contract (smart contract or proxy)" if is_likely_contract else "Wallet (EOA - Externally Owned Account)"
        
        # Pattern matching (simulated "from explorer" using known + LLM-style reasoning)
        incoming = []
        outgoing = []
        actions = []
        risks = []
        token_buys_sells = []  # Always initialize for buy/sell guidance on wallets
        
        # Simulate common flows based on patterns (in real OpenHands this would be enriched by actual explorer data via tools)
        if any(cex.lower() in lower_context for cex in known.get("cex", [])):
            incoming.append("Received from known CEX (likely user deposit)")
            risks.append("High volume from CEX - possible wash trading or large holder activity")
        
        if any(dex.lower() in lower_context for dex in known.get("dex", [])):
            outgoing.append("Sent to DEX (Uniswap/PulseX) - liquidity provision or swap")
            actions.append("Interacted with decentralized exchange for trading/liquidity")
            token_buys_sells.append("Likely bought or sold tokens via DEX")
        
        # Always add concrete guidance for wallets on buy/sell + coins (this directly addresses the user's need)
        if not token_buys_sells:
            token_buys_sells.append("To see exactly which coins were bought or sold and the full transaction history: Open the explorer and go to the 'Token Transfers' tab.")
        
        if any(p in lower_context for p in self.exploit_patterns) or "reentrancy" in lower_context or "exploit" in lower_context:
            risks.append("🚨 Address involved in known exploit patterns (reentrancy, delegatecall, flash loan, etc.) - review all interactions")
        
        if "vesting" in lower_context or "team" in lower_context:
            actions.append("Likely team/investor wallet - check vesting schedule compliance")
        
        # Market integration for value estimation (tokenomics context)
        market_value = "Unable to fetch live values"
        try:
            market = tool_hub.run_market_snapshot()
            # Simple heuristic: if context mentions tokens, estimate rough value
            if "token" in lower_context or "erc20" in lower_context:
                market_value = f"Market context available: {market[:200]}... (use for valuing transfers)"
        except:
            pass
        
        # Persistent memory integration: "αυτό το address το είδαμε ξανά"
        previous_sightings = ""
        try:
            ra = locals().get("real_activity", {}) or {}
            persistent_memory.store(
                text=f"Chain analysis for wallet {address} on {chain} - portfolio ~${ra.get('approx_usd_value',0):.0f}, categories {ra.get('categories',{})}, big native receives",
                metadata={
                    "type": "chain_analysis_wallet",
                    "address": address,
                    "chain": chain,
                    "timestamp": datetime.now().isoformat(),
                    "usd_value": ra.get("approx_usd_value", 0),
                    "categories": ra.get("categories", {}),
                    "native_in": sum(n.get("value",0) for n in ra.get("native_transfers",[]) if n.get("to")==address.lower()),
                    "top_holdings": [b.get("symbol") for b in ra.get("current_balances",[])[:4]],
                    "context": (context or "")[:150]
                }
            )
            previous_sightings = " (recorded in persistent memory for future cross-reference 'we've seen this wallet')"
        except Exception as e:
            previous_sightings = f" (memory store skipped: {e})"
        
        # PulseChain specific
        pulse_notes = ""
        if chain == "pulsechain":
            pulse_notes = "PulseChain notes: Much lower fees mean more frequent small txs. Check PulseX for DEX activity. PLS is native."
        
        # === REAL DATA FETCH using free PulseChain + PulseX public APIs (no keys) + optional Moralis ===
        real_activity = {}
        real_buysell_lines = []
        source_note = ""
        extra_sections = {}
        try:
            real_activity = self.fetch_real_token_activity(address, chain, limit=40)
            src = real_activity.get("source", "none")
            if src != "none":
                if "moralis" in src:
                    source_note = f"Real on-chain data enhanced with Moralis (free tier key) + public fallbacks ({src})."
                else:
                    source_note = f"Real on-chain data fetched via free public APIs ({src}). No API key required."
                b = real_activity.get("bought", [])
                s = real_activity.get("sold", [])
                if b or s:
                    real_buysell_lines.append("=== REAL BUY/SELL + ACTIVITY (fetched live) ===")
                    for x in b[:6]:
                        real_buysell_lines.append(f"  {x}")
                    for x in s[:6]:
                        real_buysell_lines.append(f"  {x}")
                    if real_activity.get("errors"):
                        real_buysell_lines.append(f"(some sources had transient errors: {real_activity['errors'][:1]})")
                else:
                    real_buysell_lines.append("No recent token activity found via free APIs (wallet may be quiet or new).")

                # Extra rich data from Moralis when available
                if real_activity.get("native_transfers"):
                    extra_sections["native_pls_flows"] = [f"{n.get('value',0):,.2f} PLS { 'IN' if n.get('to')==address else 'OUT' } @ {n.get('datetime','')}" for n in real_activity["native_transfers"][:5]]
                if real_activity.get("current_balances"):
                    extra_sections["current_portfolio"] = real_activity["current_balances"][:8]
                    extra_sections["approx_usd_value"] = real_activity.get("approx_usd_value", 0)
                if real_activity.get("categories"):
                    extra_sections["activity_categories"] = real_activity["categories"]
                if real_activity.get("approvals"):
                    extra_sections["recent_approvals"] = real_activity["approvals"][:3]
                if real_activity.get("pnl_estimate"):
                    extra_sections["pnl_estimate"] = real_activity["pnl_estimate"]
                if real_activity.get("risk_score"):
                    extra_sections["risk_score"] = real_activity["risk_score"]
            else:
                real_buysell_lines.append("Free API sources returned no data (using guidance fallback).")
        except Exception as e:
            real_buysell_lines.append(f"Real API fetch error (using manual guidance): {str(e)[:100]}")
            log.warning(f"Real token activity fetch failed: {e}")

        final_token_history = real_buysell_lines if real_buysell_lines else (token_buys_sells or [
            "No buy/sell signals in the provided context.",
            "**To get the real transaction history and which coins were bought or sold:**",
            f"1. Open the explorer link: {explorer_link}",
            "2. Go to the **'Token Transfers'** tab — this is the key tab for buy/sell history.",
            "3. **Incoming** ERC20 transfers = coins the wallet bought or received.",
            "4. **Outgoing** ERC20 transfers = coins the wallet sold or sent.",
            "Common coins to watch on PulseChain: WPLS, USDT, HEX, PLSX, etc.",
            "5. Click on a token row to see the full history for that specific coin."
        ])

        # Build rich full wallet profile (most important for agents)
        full_profile = {
            "address": address,
            "chain": chain,
            "activity_level": real_activity.get("activity_level", "unknown"),
            "onchain_nonce": real_activity.get("onchain_nonce"),
            "native_pls_summary": real_activity.get("native_transfers", [])[:3],
            "token_portfolio": real_activity.get("current_balances", [])[:6],
            "estimated_usd": real_activity.get("approx_usd_value", 0),
            "top_categories": dict(sorted(real_activity.get("categories", {}).items(), key=lambda x: -x[1])[:5]),
            "recent_swaps": [b for b in real_activity.get("bought", []) if "swap" in b.lower()] + [s for s in real_activity.get("sold", []) if "swap" in s.lower()][:4],
            "approvals_count": len(real_activity.get("approvals", [])),
            "pnl_estimate": real_activity.get("pnl_estimate", {}),
            "risk_score": real_activity.get("risk_score", {}),
            "large_ecosystem_movements": real_activity.get("large_ecosystem_movements", []),
            "ecosystem_alerts": real_activity.get("ecosystem_alerts", []),
        }

        report = {
            "address": address,
            "chain": chain,
            "type": address_type,
            "explorer_link": explorer_link,
            "summary": f"Address {address} on {chain} appears to be a {address_type.lower()}. {previous_sightings}",
            "incoming_flows": incoming or ["No specific incoming patterns detected from context/explorer patterns. Check full tx history on explorer."],
            "outgoing_flows": outgoing or ["No specific outgoing patterns detected. Look for contract creations or large transfers."],
            "what_it_did": actions or ["General activity - review recent transactions for DeFi interactions, transfers, or contract calls."],
            "token_buy_sell_history_and_coins": final_token_history,
            "full_wallet_profile": full_profile,
            "risks_and_flags": risks or ["No high risks flagged from context. Verify full history on explorer."],
            "market_context_for_tokenomics": market_value,
            "pulsechain_specific": pulse_notes,
            "large_ecosystem_movements": real_activity.get("large_ecosystem_movements", []),
            "ecosystem_alerts": real_activity.get("ecosystem_alerts", []),
            "recommendations": [
                f"1. **Most important for buy/sell history**: Open {explorer_link} and immediately go to the **'Token Transfers'** tab.",
                "   - Incoming = coins bought or received (with exact token symbol and amount).",
                "   - Outgoing = coins sold or sent.",
                "2. Also check the 'Transactions' tab for native PLS (gas) movements and the 'Internal Txns' tab for contract calls.",
                "3. Filter by date/value to spot large buys/sells.",
                "4. For context on which DEX or protocol was used, look at the 'to' address in the transfers.",
                "5. Use the market snapshot to estimate the USD value of the coins at the time of the tx.",
                "6. Large movements of HEX, PLSX, INC are now flagged in 'large_ecosystem_movements' / 'ecosystem_alerts' with USD value (same philosophy as native PLS: real $ thresholds, small moves ignored).",
                "7. If you have more context (e.g. specific tx hashes or 'it interacted with this contract'), provide it and I can refine the analysis."
            ],
            "how_to_use_in_openhands": "Use the native MCP analyze_wallet tool (preferred) or call analyze_address / run_task with the address. Real data is already fetched (Moralis if key + public BlockScout/PulseX/RPC). The report includes actionable steps + full raw activity. No browser needed; use the returned real_buy_sell_history etc. directly."
        }

        if source_note:
            report["data_source"] = source_note
            report["real_activity"] = real_activity  # full raw for advanced use

        # Merge extra rich sections (native, portfolio, categories, approvals, pnl, risk)
        report.update(extra_sections)

        # Ensure top-level for easy access pre run_task
        if "pnl_estimate" not in report and "pnl_estimate" in real_activity:
            report["pnl_estimate"] = real_activity["pnl_estimate"]
        if "risk_score" not in report and "risk_score" in real_activity:
            report["risk_score"] = real_activity["risk_score"]

        # Automatically append the ultra-specific guidance for real buy/sell data
        if address_type.startswith("Wallet"):
            extra_guidance = self.get_real_buy_sell_history_guidance(address, chain)
            report["actionable_agent_steps_for_real_history"] = extra_guidance
            # Also provide structured real fetch result
            try:
                real_hist = self.get_real_buy_sell_history(address, chain)
                report["real_buy_sell_history"] = real_hist
            except Exception:
                pass

            # Real visualization (most useful for agents)
            try:
                viz = self.visualize_flows(address, chain, context)
                report["flow_visualization"] = viz
            except Exception:
                pass
        
        print(f"🔗 Enhanced Chain Analysis complete for {address[:10]}... on {chain}. Explorer: {explorer_link}")
        return report

    def get_real_buy_sell_history_guidance(self, address: str, chain: str = "pulsechain") -> str:
        """Πολύ συγκεκριμένη, actionable οδηγία για τον agent να βγάλει πραγματικό buy/sell ιστορικό με coins.
        (Updated: now also attempts free public PulseChain BlockScout + PulseX GraphQL + RPC automatically first.)
        """
        explorer = self.known_patterns.get(chain, self.known_patterns["pulsechain"])["explorer_base"] + address
        return f"""
**ΒΗΜΑ-ΒΗΜΑ ΓΙΑ ΠΡΑΓΜΑΤΙΚΟ BUY/SELL ΙΣΤΟΡΙΚΟ + COINS (κάνε ακριβώς αυτό):**

1. Άνοιξε αυτό το URL: {explorer}
2. Κάνε κλικ στο tab **"Token Transfers"** (όχι Transactions).
3. Κάνε sort by Date (νεότερα πρώτα).
4. Για τις τελευταίες 30-50 εγγραφές:
   - Αν είναι **Incoming** (πράσινο/από αριστερά): Το wallet **αγόρασε ή έλαβε** το token (γράψε symbol + ποσότητα + ημερομηνία).
   - Αν είναι **Outgoing** (κόκκινο): Το wallet **πούλησε ή έστειλε** το token.
5. Ιδιαίτερα πρόσεξε interactions με PulseX/Uniswap router — αυτά είναι swaps (buy/sell).
6. Επίστρεψε τα αποτελέσματα σε μορφή:
   - Bought: 1,234.56 USDT on 2024-...
   - Sold: 50,000 HEX on 2024-...
7. Μετά φέρε μου τα και θα τα αναλύσουμε με market data για κέρδη/ζημιές.

(Σημείωση: Ο expert τώρα προσπαθεί ΑΥΤΟΜΑΤΑ πρώτα free public APIs: BlockScout tokentx, PulseX GraphQL subgraph για swaps, και public RPC logs. Αν πετύχει βλέπεις πραγματικά δεδομένα απευθείας στο report χωρίς manual browse.)

Αυτό θα σου δώσει **πραγματική** ιστορία, όχι simulation.
"""

    def analyze_contract_creator(self, contract_address: str, chain: str = "ethereum", context: str = "") -> dict:
        """Dedicated contract creator/deployer analysis (critical for audits and exploit tracing)."""
        log.info(f"Chain Analysis: Analyzing creator/deployer of contract {contract_address}")
        # Heuristic: if context has other addresses, use first as potential creator
        addresses = re.findall(r'0x[a-fA-F0-9]{40}', context)
        creator = addresses[0] if addresses else "0x0000000000000000000000000000000000000000"
        base = self.analyze_address(creator, chain, context + f" contract creator analysis for {contract_address}")
        base["note"] = f"Analysis for the *creator/deployer* of contract {contract_address}. Always verify the exact creation tx on the explorer to see constructor arguments and confirm the deployer."
        base["recommendations"].append(f"8. On explorer for {contract_address}, locate the 'Contract Creation' transaction to get the precise deployer and verify if source code is published.")
        return base

    def visualize_flows(self, address: str, chain: str = "pulsechain", context: str = "") -> dict:
        """Real data-driven visualization (ASCII + Mermaid) using actual API results.
        Much better than stub when we have real_activity.
        """
        log.info("Chain Analysis: Generating real-data flow visualization")
        # Avoid recursion: fetch real data directly instead of calling analyze_address (which calls back to visualize for wallets)
        ra = self.fetch_real_token_activity(address, chain) or {}

        # Build from real data
        native_in = sum(n.get("value", 0) for n in ra.get("native_transfers", []) if n.get("to") == address.lower())
        native_out = sum(n.get("value", 0) for n in ra.get("native_transfers", []) if n.get("from") == address.lower())

        portfolio = ra.get("current_balances", [])[:5]
        buys = ra.get("bought", [])[:4]
        sells = ra.get("sold", [])[:4]
        cats = ra.get("categories", {})

        ascii_viz = f"""
REAL FLOW for {address[:10]}... on {chain} (data from Moralis+free APIs):

External Sources (big receives)
        |
        v
Wallet {address[:10]}...   <--- received ~{native_in:,.0f} PLS (native)
        |
        +-- token receives & swaps (categories: {list(cats.keys())[:3]})
        |
        v
Current Holdings (top):
"""
        for p in portfolio:
            ascii_viz += f"        - {p.get('symbol')}: ~${p.get('usd',0):.0f}\n"

        ascii_viz += f"""
        |
        v
DEX activity (PulseX swaps): {len(buys)+len(sells)} notable
Buys: {', '.join([b[:40] for b in buys]) or 'none recent'}
Sells: {', '.join([s[:40] for s in sells]) or 'none recent'}
"""

        mermaid = f"""
```mermaid
flowchart TD
    EXT[External / Airdrops / Big Transfers] -->|~{native_in:,.0f} PLS| W[Wallet {address[:8]}...]
    W -->|token receives + {cats.get('token swap',0)} swaps| DEX[PulseX / DeFi]
    DEX -->|swaps into| TOK[HEX, PLSX, PCOCK, memes...]
    W -->|current holdings| PORT[Portfolio ~${ra.get('approx_usd_value',0):.0f}]
    style W fill:#aaffaa,stroke:#333
    style DEX fill:#ffddaa
```
"""

        return {
            "ascii": ascii_viz,
            "mermaid": mermaid,
            "summary": f"Wallet received large native PLS, holds diversified PulseChain tokens (~${ra.get('approx_usd_value',0):.0f}), did {cats.get('token swap',0)} swaps + many receives.",
            "raw_data_used": {"native_in": native_in, "portfolio_top": [p.get('symbol') for p in portfolio], "categories": cats}
        }

    def _estimate_pnl_with_market(self, activity: dict, chain: str) -> dict:
        """Better PnL estimate using market data (from tool_hub snapshot) + holdings + native inflows.
        For PulseChain memes it's approximate (no deep historical for all tokens).
        Focus: current portfolio value + note large 'free' PLS receives as major positive PnL contributor.
        """
        current_usd = activity.get("approx_usd_value", 0) or 0
        native_in_pls = sum(
            n.get("value", 0) for n in activity.get("native_transfers", [])
            if n.get("to") == activity.get("address", "").lower()
        )
        # Rough: assume current WPLS/PLS price from Moralis balances or snapshot ~ very low
        # Since Moralis already gives usd for WPLS holdings, the native inflows' current value is largely PnL (zero cost basis likely)
        pls_pnl_contrib = 0
        for b in activity.get("current_balances", []):
            if b.get("symbol", "").upper() in ["PLS", "WPLS"]:
                pls_pnl_contrib += b.get("usd", 0)

        # The two `if` branches that used to build market_note here were dead:
        # the line after them overwrote the variable unconditionally. Only the
        # snapshot text ever survived, so the HEX/PLSX checks did nothing.
        try:
            snap = tool_hub.run_market_snapshot()
            market_note = (str(snap)[:250] + "...") if snap else ""
        except Exception:
            market_note = "Additional market snapshot unavailable."

        # THERE IS NO PnL HERE, AND THERE CANNOT BE.
        #
        # This used to report `estimated_unrealized_pnl_usd = pls_pnl_contrib
        # * 0.9` — the current value of the wallet's PLS/WPLS holdings times a
        # constant. That is not a profit calculation. Profit is exit value minus
        # entry cost, and no entry cost is fetched anywhere in this function or
        # in the data it is given. The 0.9 encoded a guess ("most PLS inflows
        # are gain") as a dollar figure, under a key that reads as a
        # measurement, in a wallet report.
        #
        # What IS measured is kept, under names that say what it is. The PnL key
        # stays in the dict so nothing downstream raises, and it is None —
        # because the honest answer to "what is the PnL" here is "unknown".
        return {
            "current_portfolio_usd": round(current_usd, 2),
            "estimated_unrealized_pnl_usd": None,
            "pnl_available": False,
            "pnl_unavailable_reason": (
                "No cost basis. PnL needs an entry price per position and none is "
                "fetched — historical per-transaction prices are not available "
                "through this path. Any number here would be invented."
            ),
            "native_holdings_value_usd": round(pls_pnl_contrib, 2),
            "native_received_pls": round(native_in_pls, 2),
            # Kept under their old names so existing callers keep working.
            "big_native_pls_contrib_pls": round(native_in_pls, 2),
            "big_native_pls_contrib_usd_approx": round(pls_pnl_contrib, 2),
            "note": (
                "Current holdings and native inflows are measured. PnL is NOT "
                "computed: without an entry cost per position it cannot be, and "
                "a large PLS receive is not by itself a gain — it may be a "
                "transfer between the owner's own wallets."
            ),
            "market_data_context": market_note[:300] if market_note else "No extra market prices fetched."
        }

    def _calculate_risk_score(self, activity: dict, chain: str) -> dict:
        """Risk scoring tailored to observed patterns like 'big PLS receive + low activity + meme bag'.
        Score 0-100. Higher = more caution for audits / tokenomics / tracing.

        EXACT USER ECONOMIC RULES (hardened, never change without explicit new instruction):
        - Big native PLS receive is measured in USD value, NOT raw coin count.
          Reason: PLS is extremely cheap on PulseChain (~0.000007$), so 1M-5M+ coins can still be tiny real value.
        - Real "big" starts at meaningful USD: >50000 very large, >10000 large, >1000 notable, >100 small.
        - Small inflows ($50, $100, $500) MUST NOT trigger heavy analysis or high risk flags.
        - The "big PLS receive + low activity + meme bag" pattern_match only fires when USD thresholds + low nonce + multiple meme tokens are all true.
        """
        score = 0
        reasons = []
        recommendations = []

        # 1. Big PLS receive (sudden large native influx - now measured in USD value, not raw coins,
        # because on PulseChain PLS is very cheap (~0.000007 USD), so 1M-5M+ coins can be small $ value.
        # We compute approximate USD using current_balances (Moralis) or fallback price.
        native_in_pls = sum(
            n.get("value", 0) for n in activity.get("native_transfers", [])
            if n.get("to") == activity.get("address", "").lower()
        )

        # Derive PLS price from current_balances if we have WPLS/PLS with usd + balance
        pls_price = 0.000007  # very conservative fallback (~$0.000007)
        for b in activity.get("current_balances", []):
            sym = (b.get("symbol") or "").upper()
            if sym in ["WPLS", "PLS"]:
                try:
                    bal = float(str(b.get("balance", "0")).replace(",", "") or 0)
                    usd_val = float(b.get("usd", 0) or 0)
                    if bal > 0:
                        pls_price = usd_val / bal
                        break
                except:
                    pass

        native_in_usd = native_in_pls * pls_price

        # Tiered by real USD value (user feedback: on PulseChain, real "big" starts much higher,
        # small $50/$100/$500 inflows should not add heavy risk score)
        if native_in_usd > 50000:
            score += 45
            reasons.append(f"Very large native PLS receive worth ~${native_in_usd:,.2f} ({native_in_pls:,.0f} PLS @ ~${pls_price:.8f} each) - possible airdrop, claim, or large distribution. High chance of future sell pressure.")
        elif native_in_usd > 10000:
            score += 30
            reasons.append(f"Large native PLS inflow worth ~${native_in_usd:,.2f} ({native_in_pls:,.0f} PLS) - monitor for dumps.")
        elif native_in_usd > 1000:
            score += 15
            reasons.append(f"Notable native PLS inflow worth ~${native_in_usd:,.2f} ({native_in_pls:,.0f} PLS) - monitor.")
        elif native_in_usd > 100:
            score += 5
            reasons.append(f"Small native PLS inflow worth ~${native_in_usd:,.2f} ({native_in_pls:,.0f} PLS).")

        # 2. Low on-chain activity
        nonce = activity.get("onchain_nonce")
        if nonce is not None and nonce < 10:
            score += 25
            inflow_desc = f"large receives (~${native_in_usd:.2f})" if native_in_usd > 1000 else f"receives (~${native_in_usd:.2f})"
            reasons.append(f"Extremely low activity (nonce={nonce}) - fresh wallet or minimal usage. Combined with {inflow_desc}: classic airdrop recipient or farming pattern.")
        elif nonce is not None and nonce < 30:
            score += 15
            reasons.append("Low transaction count - limited history, harder to trust long-term behavior.")

        # 3. Meme / low-cap bag (many small unknown tokens)
        meme_like = 0
        meme_hints = ["PCOCK", "PTIGER", "OMEGA", "ZELDA", "RHPEPE", "INC", "PRVX", "pTGC", "UNITY", "ZERØ"]
        for b in activity.get("current_balances", []):
            sym = (b.get("symbol") or "").upper()
            if any(h in sym for h in meme_hints) or b.get("usd", 0) < 50:  # small value often meme
                meme_like += 1
        if meme_like >= 4:
            score += 20
            reasons.append(f"Meme/low-cap heavy bag ({meme_like} tokens) - high volatility and rug risk. Typical in PulseChain small cap plays.")
        elif meme_like >= 2:
            score += 10
            reasons.append("Several low-cap / meme tokens in holdings.")

        # 4. Heavy receive vs active trading
        receives = activity.get("categories", {}).get("token receive", 0) + activity.get("categories", {}).get("receive", 0)
        swaps = activity.get("categories", {}).get("token swap", 0)
        if receives > 10 and swaps < 3:
            score += 10
            reasons.append("Many passive receives + few swaps - may be farming/distribution wallet rather than active user.")

        # 5. Approves without clear long history
        if len(activity.get("approvals", [])) >= 3 and (nonce or 0) < 20:
            score += 5
            reasons.append("Multiple approvals with low overall activity - potential DeFi interaction or phishing prep.")

        # 6. Large movements of key Pulsechain ecosystem tokens (HEX, PLSX, INC) - NEW
        # Uses same USD philosophy: we care about real dollar value, not raw token count.
        # Large moves of these can signal smart money, distributions, or liquidity events.
        large_eco = activity.get("large_ecosystem_movements", []) or []
        eco_usd = sum(m.get("usd_value", 0) for m in large_eco)
        if eco_usd > 50000:
            score += 25
            reasons.append(f"Very large ecosystem token movements (HEX/PLSX/INC) worth ~${eco_usd:,.0f} USD - monitor for coordinated activity or major holder behavior.")
        elif eco_usd > 10000:
            score += 15
            reasons.append(f"Large ecosystem token movements (HEX/PLSX/INC) ~${eco_usd:,.0f} USD.")
        elif eco_usd > 1000:
            score += 5
            reasons.append(f"Notable ecosystem token activity (HEX/PLSX/INC) ~${eco_usd:,.0f} USD.")

        total = min(100, score)
        if total >= 70:
            level = "HIGH"
            recommendations.append("Strong caution: possible distribution recipient or low-conviction holder. Watch for coordinated sells on PulseX.")
        elif total >= 45:
            level = "MEDIUM"
            recommendations.append("Monitor closely. Significant inflows + meme exposure common in rugs or hype cycles on PulseChain.")
        else:
            level = "LOW"
            recommendations.append("Relatively normal for PulseChain airdrop-style wallet. Still verify source of large PLS inflows.")

        return {
            "score": total,
            "level": level,
            "reasons": reasons,
            "recommendations": recommendations,
            "pattern_match": "big PLS receive + low activity + meme bag" if (native_in_usd > 10000 and (nonce or 99) < 20 and meme_like >= 2) else "general wallet risks",
            "native_inflow_usd": round(native_in_usd, 2),
            "native_inflow_pls": round(native_in_pls, 2),
            "pls_price_used": round(pls_price, 10)
        }

    def trace_flows(self, address: str, chain: str = "ethereum", direction: str = "both") -> str:
        """Specialized for tracing sends/receives."""
        analysis = self.analyze_address(address, chain)
        return f"""
TRACE SUMMARY for {address} ({direction} on {chain}):
Incoming: {analysis['incoming_flows']}
Outgoing: {analysis['outgoing_flows']}
Key Actions: {analysis['what_it_did']}
Risks: {analysis['risks_and_flags']}
Explorer: {analysis['explorer_link']}

Full details: See analyze_address report.
"""

# Register
chain_analysis_expert = ChainAnalysisExpert()
