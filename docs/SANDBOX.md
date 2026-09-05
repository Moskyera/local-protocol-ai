# Sandboxing Agent Canvas

Agent Canvas runs its **agent-server** — the part that executes shell commands
and edits files — on your machine, as you, with everything you can reach. The
OpenHands project says this itself and keeps its older Docker interface alive
for exactly this reason. This is the one real gap in this project's otherwise
loopback-only, no-network posture.

This is one way to close the filesystem half of that gap on Windows, using WSL.
It is not the only way and it is not perfect. Read what it does and does not do
before you rely on it.

## What it is

- The **agent-server and its terminal run inside WSL, as a separate Linux user**
  (`lpai-agent`) who has no password, no sudo, and **cannot read your Windows
  drive**. That user has his own home and his own copy of Node, uv and Canvas.
- The **model and your MCP tools stay on Windows**, bound to the WSL network
  adapter address only (not `0.0.0.0`, so not your LAN), and the agent reaches
  them there on purpose.
- The **browser UI is the same** `http://localhost:8000`.

So: the agent can run whatever it likes, but the blast radius is a throwaway
Linux home directory, not your Documents, your `.env`, or your keys.

## What it is NOT

- **Not an air gap.** The agent can reach the network. It reaches the model and
  the tool server by design, and WSL routes it to the internet like any Linux
  box. If you need the agent to have no network at all, this is the wrong tool.
- **Not protection against a malicious model reading its own context.** Whatever
  you type, and whatever the tools return, the agent sees. The sandbox is about
  what the agent's *commands* can touch, not what the agent *knows*.
- **Not a Windows-side jail.** The model and tool servers still run as you on
  Windows. A flaw in *them* is not contained by this. It contains the agent's
  shell, which is where arbitrary, model-decided commands actually run.
- **Not verified end to end here.** The plumbing was measured (below). The
  isolation *mechanism* — the unprivileged user, the hidden drive — is created
  and checked by the setup script and refused-if-absent by the launcher. A full
  agent task was **not** run inside the applied sandbox during development,
  because applying it needs your `sudo` and a `wsl --shutdown` that only you can
  run. Treat the isolation as "set up correctly and checked", not "battle-tested".

## Setup, once

You need WSL with an Ubuntu distro (`wsl --install -d Ubuntu`), and the Windows
stack already working (`start-canvas.bat` runs).

```bash
wsl -d Ubuntu
sudo bash /mnt/c/AI/market-agent/scripts/sandbox-canvas-setup.sh
exit
wsl --shutdown
```

The setup script, which asks for your WSL password once for `sudo`:

1. Creates the user `lpai-agent` — no password, no sudo.
2. Sets `/etc/wsl.conf` so every Windows drive is mounted `umask=077`, i.e.
   readable only by your own WSL user. It **merges** this into any existing
   `wsl.conf`; it does not overwrite your other settings.
3. Installs Node 22, uv and Agent Canvas into `lpai-agent`'s home only.

`wsl --shutdown` is what applies step 2. It closes every WSL session you have
open, so save your work first. Then confirm the wall is real:

```bash
wsl -d Ubuntu -u lpai-agent -- ls /mnt/c
```

That must print **`Permission denied`**. If it lists your drive, the shutdown
did not happen and the sandbox is not active.

## Running

```bat
start-canvas-sandboxed.bat
```

It refuses to start if `lpai-agent` does not exist, or if that user can still
read `C:` — it will not pretend to sandbox you. It discovers the WSL adapter
address fresh each start (NAT-mode WSL can renumber on reboot), binds the model
and tools there, and launches Canvas in WSL as `lpai-agent`.

**Open the UI with `http://localhost:8000`, not `http://127.0.0.1:8000`.** WSL's
localhost forwarding relayed only IPv6 loopback in testing; a browser tries both
and works, but a tool pinned to the IPv4 literal will not reach it.

The sandboxed backend keeps its **own** settings store (in `lpai-agent`'s home),
separate from the Windows one. So the first time, set the model and MCP server
in Settings, using the two URLs the launcher prints — the WSL adapter address,
not `localhost`, because from inside WSL `localhost` is WSL itself:

- Model base URL: `http://<WSL-adapter>:8080/v1`, key `sk-dummy-local`
- MCP server: `http://<WSL-adapter>:8765/mcp`, transport `streamable-http`

## What was measured

On this machine (WSL 2.7.3, NAT networking, one Ubuntu distro), with throwaway
listeners and the real stack:

- WSL → Windows on the adapter address works both ways; loopback binds on either
  side are **not** reachable from the other, which is why the model and tools
  are bound to the adapter, not to `127.0.0.1`.
- With the whole Canvas inside WSL, Windows reaches it at `localhost:8000` via
  localhost forwarding (IPv6), and the session-key auth holds through the relay:
  `200` with the key, `401` without it and with a wrong one.
- The WSL backend, pointed at the Windows model and tool servers on the adapter
  address, connected to both (`/health` 200, the MCP `initialize` handshake 200)
  and issued shell requests that ran inside WSL.
- The model and MCP servers bound to the WSL adapter address only, never
  `0.0.0.0`, so nothing on your LAN can see them.

## Undoing it

```bash
wsl -d Ubuntu
sudo userdel -r lpai-agent               # remove the user and his home
sudo sed -i '/umask=077/d' /etc/wsl.conf # or edit [automount] back by hand
exit
wsl --shutdown
```
