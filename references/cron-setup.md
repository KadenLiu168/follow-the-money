# Cron Setup

OS-specific instructions for running the local skill on a schedule. Load this when the user has finished onboarding and needs to automate the digest.

## Required Environment Variable

`FTM_SKILL_DIR` must point to the absolute path of the cloned repository.

```bash
# macOS / Linux
export FTM_SKILL_DIR=/Users/you/code/follow-the-money

# Windows (PowerShell)
$env:FTM_SKILL_DIR = "C:\code\follow-the-money"
```

The scripts read this to locate `prompts/`, `lib/`, and the local node_modules. Without it, `node scripts/prepare-digest.js` will fail with "prompts directory not found".

## Recommended Schedule

| Job | Frequency | Why |
|---|---|---|
| Digest | 1× per day at user's chosen time | Matches center's 2×/day aggregator |
| Alert check | 4-6× per day | Catches 13D filings within hours |

The center updates the feed twice daily (08:00 ET + 20:00 ET). Local cron more frequent than that is harmless — `check-alerts.js` exits 0 silently when there's nothing new.

## macOS / Linux — crontab

Edit your crontab:

```bash
crontab -e
```

Add these lines (adjust times to your config):

```cron
# Daily digest at 08:00 local time
0 8 * * * cd $FTM_SKILL_DIR && /usr/local/bin/node scripts/prepare-digest.js > ~/.follow-the-money/digest.json && /usr/local/bin/node scripts/deliver.js --file ~/.follow-the-money/digest.json >> ~/.follow-the-money/cron.log 2>&1

# Alert check every 4 hours
0 */4 * * * cd $FTM_SKILL_DIR && /usr/local/bin/node scripts/check-alerts.js >> ~/.follow-the-money/cron.log 2>&1
```

**Notes:**
- Use absolute paths to `node` (run `which node` to find it)
- `cd $FTM_SKILL_DIR` is required — scripts resolve relative paths from cwd
- The default `--lookback` is 90 days (one quarter) — 13F is quarterly. To run "today only" instead, append `--lookback 1`.
- Logs go to `~/.follow-the-money/cron.log`; rotate if it grows large

To find your `node` path:

```bash
which node
# /usr/local/bin/node
# or /opt/homebrew/bin/node (Apple Silicon)
# or /home/you/.nvm/versions/node/v20.x.x/bin/node (nvm)
```

## Linux — systemd timer (alternative)

If your system uses systemd, prefer a user-level timer over crontab.

`~/.config/systemd/user/ftm-digest.service`:

```ini
[Unit]
Description=Follow the Money — daily digest

[Service]
Type=oneshot
Environment=FTM_SKILL_DIR=/home/you/code/follow-the-money
WorkingDirectory=%h/code/follow-the-money
ExecStart=/usr/bin/node scripts/prepare-digest.js
```

`~/.config/systemd/user/ftm-digest.timer`:

```ini
[Unit]
Description=Run FTM digest daily at 08:00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ftm-digest.timer
systemctl --user list-timers
```

## Windows — Task Scheduler

### One-time setup

Open PowerShell as your normal user (no admin needed for user-level tasks).

```powershell
# Set the env var persistently for your user
[Environment]::SetEnvironmentVariable("FTM_SKILL_DIR", "C:\code\follow-the-money", "User")

# Close and reopen the shell so the new var is visible
```

### Create the daily digest task

```powershell
$action = New-ScheduledTaskAction `
  -Execute "node.exe" `
  -Argument "scripts\prepare-digest.js" `
  -WorkingDirectory $env:FTM_SKILL_DIR

$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

Register-ScheduledTask `
  -TaskName "FTM-Daily-Digest" `
  -Action $action `
  -Trigger $trigger `
  -Description "Follow the Money daily digest"
```

### Create the alert check task (every 4 hours)

```powershell
$action = New-ScheduledTaskAction `
  -Execute "node.exe" `
  -Argument "scripts\check-alerts.js" `
  -WorkingDirectory $env:FTM_SKILL_DIR

$trigger = New-ScheduledTaskTrigger `
  -Once -At "00:00" `
  -RepetitionInterval (New-TimeSpan -Hours 4) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask `
  -TaskName "FTM-Alert-Check" `
  -Action $action `
  -Trigger $trigger `
  -Description "Follow the Money 13D alert check"
```

### Verify

```powershell
Get-ScheduledTask -TaskName "FTM-Daily-Digest"
Get-ScheduledTask -TaskName "FTM-Alert-Check"
```

Test by running the action manually:

```powershell
Start-ScheduledTask -TaskName "FTM-Daily-Digest"
```

Check `~/.follow-the-money/cron.log` (or the task's history) for output.

## Verifying the Install

After the first scheduled run:

1. Check the log file: `tail -50 ~/.follow-the-money/cron.log`
2. Confirm a digest arrived (stdout / Telegram / email)
3. Confirm `config.lastAlertTimestamp` updated (no alerts on day 1 is normal)
4. Wait for an SC 13D filing on a tracked issuer — verify the alert lands

If nothing arrives:
- Check `node` is on PATH for the cron user (cron has minimal env)
- Verify `FTM_SKILL_DIR` is set in the cron's environment, not just your interactive shell
- Run the script manually from the cron user's shell to reproduce

## Uninstall

- **macOS / Linux crontab**: `crontab -e` and remove the FTM lines
- **Linux systemd**: `systemctl --user disable --now ftm-digest.timer`
- **Windows**: `Unregister-ScheduledTask -TaskName "FTM-Daily-Digest"` (and the alert task)

The skill is fully uninstalled once the schedule is gone. Feed files in the repo and config in `~/.follow-the-money/` are independent and can stay or be deleted at your discretion.
