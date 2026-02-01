# Verifiable Agent Protocol

Use Triple Handshake ONLY for STATE-CHANGING ACTIONS that can be verified.

## When TO Use (action tasks with persistent results)
- "Kill process X" → verify process no longer exists
- "Delete file Y" → verify file is gone
- "Stop service Z" → verify service stopped
- "Create backup" → verify backup file exists

## When NOT To Use (query tasks with transient results)
- "Check CPU usage" → just call get_system_health and report
- "List processes" → just run command and report results
- "What's memory usage?" → just report current snapshot

These metrics change every second - verification would always fail!

## Triple Handshake Steps

**FOR QUERY TASKS:** Just use tools directly and report results. No assign_mission needed.

**FOR ACTION TASKS:**
1. `assign_mission(goal, verification_criteria)`
   - Example: `verification_criteria: '{"type": "process_killed", "pid": 1234}'`
2. Execute the action (kill process, delete file, etc.)
3. `report_execution(mission_id, summary)`

## Example - Kill Process
```
assign_mission("Kill high-CPU process", '{"type": "process_killed", "pid": 41652}')
run_terminal_command("taskkill /PID 41652 /F")
report_execution("abc123", "Process 41652 terminated")
```
