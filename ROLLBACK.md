# Rollback / Recovery Instructions for MOSKY AI Workstation

**Current stable state**: `stable-2026-06-12`

Everything (except the sacred Telegram/briefing part) has been reorganized and verified to work flawlessly.

## Best Way: Git (Recommended)

We have initialized Git in this folder with a clean `.gitignore`.

### To see current history:
```powershell
git log --oneline
git tag
```

### To instantly revert to the current flawless state (no matter what breaks later):
```powershell
git checkout stable-2026-06-12
```

Or to go back to the exact commit:
```powershell
git checkout stable-2026-06-12 -- .
```

After checkout, you may need to:
- Restart the workstation (`start-ai.bat`)
- Rebuild the Docker image if you changed `runtime/Dockerfile`:
  ```powershell
  docker build -t my-openhands-runtime -f runtime/Dockerfile .
  ```

### To create a new experiment safely:
```powershell
git checkout -b my-experiment-2026-06-xx
# ... do your dangerous changes ...
```

If it breaks:
```powershell
git checkout stable-2026-06-12
```

### To permanently keep good changes:
```powershell
git checkout stable-2026-06-12
git merge my-experiment-2026-06-xx
git tag stable-2026-06-xx-new   # optional new stable tag
```

## Simple Full Backup (if you prefer zip)

Run this script before risky changes:

```powershell
.\backup_current_state.ps1
```

It will create a timestamped zip of the `market-agent` source code (excluding venvs, models, llama binaries, logs, pycache etc.).

To restore:
1. Rename or delete the current `market-agent` folder (or just the files you broke).
2. Extract the zip.
3. Restart `start-ai.bat`.

## What is NOT easy to "revert" automatically
- The big GGUF model (`C:\AI\models\...gguf`) — 15.8 GB
- The llama/ binaries and DLLs
- The ai-env virtual environment (very large)

These are meant to be reinstalled/re-downloaded if corrupted. The code + scripts are what matter for "the state that works flawlessly".

## Sacred Rule Reminder
Never let any agent or script touch the Telegram/briefing files. They are protected by `guards.py` and should stay exactly as they are now.

## Quick Health Check After Any Revert
```powershell
cd C:\AI\market-agent
& "C:\AI\ai-env\Scripts\Activate.ps1"
python verify_system.py
```

If this shows **All 16 sections PASSED**, you're back to a good state.

---

Current stable tags (use the latest for full rollback):
- `stable-2026-06-12` — Base reorganized state (before web_research tool)
- `stable-2026-06-12-web-research` — Latest: Added safe `web_research` MCP tool (with built-in confirmation + security_risk handling) + supervisor auto-routing/preference for all site/URL/website tasks (replaces broken 'browser' tool entirely).

To rollback to the version with the new web_research enhancements:
```powershell
git checkout stable-2026-06-12-web-research
```

Then restart the stack:
```powershell
.\stop-ai.bat
.\start-ai.bat
```

Run `python verify_system.py` after to confirm health.

Run `git tag` to see available stable points in the future.
