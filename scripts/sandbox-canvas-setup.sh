#!/usr/bin/env bash
# sandbox-canvas-setup.sh — run ONCE, inside WSL Ubuntu, with sudo:
#
#     wsl -d Ubuntu
#     sudo bash /mnt/c/<path-to-repo>/scripts/sandbox-canvas-setup.sh
#
# WHAT THIS IS FOR
#   Agent Canvas runs its agent-server — the part that executes shell commands
#   and edits files — on the host, as you, with everything you can reach. The
#   OpenHands project says so itself and keeps its old Docker interface alive
#   for exactly that reason. This script builds the other half of a sandbox:
#   a second Linux user inside WSL who CANNOT see your Windows drive, with his
#   own copy of the tools the agent-server needs. start-canvas-sandboxed.bat on
#   the Windows side then runs the agent-server as that user and keeps the
#   interface on Windows.
#
# WHAT IT CHANGES (all reversible; each step says what it did)
#   1. Creates the user `lpai-agent`: no password, no sudo, home /home/lpai-agent.
#   2. Sets /etc/wsl.conf [automount] options to "metadata,umask=077,fmask=077",
#      so /mnt/c (and every other Windows drive) is readable ONLY by your own
#      WSL user. Right now it is mode 777 to every user on the system — check
#      with `stat -c %a /mnt/c`. Existing [boot]/[user] sections are kept.
#   3. Installs, as lpai-agent, into HIS home only: Node 22 LTS (nodejs.org
#      tarball), uv (astral.sh installer), and @openhands/agent-canvas.
#
# WHAT IT NEEDS FROM YOU AFTERWARDS
#   From Windows PowerShell:   wsl --shutdown
#   The automount change applies on the next WSL start. That command closes
#   every WSL session you have open. Then verify the wall is real:
#       wsl -d Ubuntu -u lpai-agent -- ls /mnt/c
#   must print "Permission denied".
#
# WHAT IT DOES NOT DO
#   It does not touch Windows, Docker, the firewall, or your own WSL user's
#   files. It does not make the agent unable to reach the network: the model
#   and tool servers on Windows are reached on purpose, on the WSL adapter
#   address only. A sandbox for the filesystem, not an air gap.

set -euo pipefail

AGENT_USER="lpai-agent"
say()  { printf '%s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || die "run with sudo:  sudo bash $0"
grep -qi microsoft /proc/version 2>/dev/null || die "this is meant to run inside WSL"
command -v curl >/dev/null || die "curl is required (apt install curl)"
command -v python3 >/dev/null || die "python3 is required"

say "=== Local Protocol AI — Canvas sandbox setup (WSL) ==="

# ---------------------------------------------------------------------------
# 1. The user
# ---------------------------------------------------------------------------
if id "$AGENT_USER" >/dev/null 2>&1; then
  say "1. user $AGENT_USER already exists (uid $(id -u "$AGENT_USER"))"
else
  useradd -m -s /bin/bash "$AGENT_USER"
  passwd -l "$AGENT_USER" >/dev/null
  say "1. created user $AGENT_USER (uid $(id -u "$AGENT_USER")), password locked, no sudo"
fi
id -nG "$AGENT_USER" | grep -qw sudo && die "$AGENT_USER is in the sudo group; that defeats the point. Remove it: gpasswd -d $AGENT_USER sudo"

# ---------------------------------------------------------------------------
# 2. Hide the Windows drives from every user but yours. Merge, do not clobber.
# ---------------------------------------------------------------------------
python3 - <<'PY'
import configparser, io, os
p = "/etc/wsl.conf"
cp = configparser.ConfigParser()
cp.optionxform = str
if os.path.exists(p):
    cp.read(p)
if not cp.has_section("automount"):
    cp.add_section("automount")
want = '"metadata,umask=077,fmask=077"'
before = cp.get("automount", "options", fallback=None)
cp.set("automount", "options", want)
buf = io.StringIO(); cp.write(buf)
text = buf.getvalue().replace(" = ", "=")
if before != want:
    with open(p, "w") as fh:
        fh.write(text)
    print(f"2. /etc/wsl.conf [automount] options: {before or '(unset)'} -> {want}")
else:
    print("2. /etc/wsl.conf already restricts /mnt/c to your user")
PY

# ---------------------------------------------------------------------------
# 3. The agent user's own toolchain. Nothing shared with yours.
# ---------------------------------------------------------------------------
say "3. installing Node 22 LTS, uv and Agent Canvas for $AGENT_USER (this downloads ~60 MB)..."
sudo -u "$AGENT_USER" -H bash -euo pipefail <<'AS_AGENT'
mkdir -p ~/.local/bin ~/.local/node ~/lpai-canvas ~/.openhands/agent-canvas
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q '^v22\.'; then
  V=$(curl -fsSL https://nodejs.org/dist/index.json | python3 -c "import json,sys; print(next(e['version'] for e in json.load(sys.stdin) if e['version'].startswith('v22.') and e.get('lts')))")
  curl -fsSL "https://nodejs.org/dist/$V/node-$V-linux-x64.tar.xz" -o /tmp/lpai-node.tar.xz
  tar -xJf /tmp/lpai-node.tar.xz -C ~/.local/node --strip-components=1
  rm -f /tmp/lpai-node.tar.xz
  ln -sf ~/.local/node/bin/node ~/.local/bin/node
  ln -sf ~/.local/node/bin/npm  ~/.local/bin/npm
  ln -sf ~/.local/node/bin/npx  ~/.local/bin/npx
fi
echo "   node $(node --version)  npm $(npm --version)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
fi
echo "   uv $(uv --version 2>/dev/null | cut -d' ' -f2)   uvx: $(command -v uvx >/dev/null && echo ok || echo MISSING)"
cd ~/lpai-canvas
[ -f package.json ] || printf '{"name":"lpai-canvas","private":true}\n' > package.json
if [ ! -f node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs ]; then
  npm install --silent @openhands/agent-canvas
fi
echo "   agent-canvas $(node node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs --version 2>&1 | head -1)"
AS_AGENT

say ""
say "Done. Two things are yours to do:"
say "  1. From Windows PowerShell:   wsl --shutdown        (closes every WSL session)"
say "  2. Then verify the wall:      wsl -d Ubuntu -u $AGENT_USER -- ls /mnt/c"
say "     It must print 'Permission denied'. If it lists your drive, the sandbox is not on."
say ""
say "After that, start the stack with start-canvas-sandboxed.bat on Windows."
