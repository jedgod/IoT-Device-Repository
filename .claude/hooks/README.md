# Automatic GitHub updates

The project Stop hook commits all non-ignored repository changes and pushes the
current branch to `jedgod/IoT-Device-Repository` after each completed Claude Code
response. This includes changes made outside Claude Code that are present at that
time. Ignored files remain ignored. GitHub authentication must already be available.

Restart Claude Code after installing this configuration. Pushes never force-update
the remote. Conflicts, an active merge/rebase, authentication errors, or a rejected
push produce an error and leave local work intact. Pending commits are retried on
the next completed response.

Manual retry from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/push-updates.ps1
```

To disable automatic sync, remove the Stop hook from `.claude/settings.json`.
