# Forensic Investigation Workflow

## Incident Resolution Flow
1. **DIAGNOSE:** Check system health, identify the problem
2. **ANALYZE:** Identify specific process causing issues (name, PID, resource usage)
3. **EXECUTE:** Run the command - Command Guard will intercept if approval needed
4. **VERIFY:** Check system health again to confirm resolution
5. **CONFIRM:** Report the final outcome to the user

## Evidence Pattern
For audit-grade investigations, use Evidence on Demand:
- `store_evidence(claim, type, data)` - Store evidence as you find it
- `list_evidence()` - Show user what evidence is available
- `get_evidence(id)` - Retrieve specific evidence when user asks

**Best Practice:** Present CLAIMS first (brief verdicts), let user request details. Keeps mobile UI clean.

## Attack Path Visualization
After completing an investigation, use:
- `render_attack_path(title, stages, annotations)` - Generate visual attack chain diagram

The diagram renders automatically in chat with color-coded stages:
entry → execution → persistence → c2

## Process Investigation Commands
- Windows: `Get-Process | Sort-Object CPU -Descending | Select-Object -First 10`
- Linux: `ps aux --sort=-%cpu | head -10`
- Check what started it: `wmic process where processid=PID get parentprocessid,commandline`
