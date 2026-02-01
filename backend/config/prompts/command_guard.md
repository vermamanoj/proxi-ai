# Command Guard Protocol

Command Guard automatically handles approval for sensitive commands.

## How It Works
1. Execute commands directly - don't pre-ask for approval
2. If command needs approval, `run_terminal_command` returns `APPROVAL_REQUIRED:...`
3. When you see APPROVAL_REQUIRED: Tell user what command needs approval and ask "Should I proceed?"
4. When user says "yes": Retry the SAME command - it will execute this time
5. BLOCKED commands: Inform user and suggest alternatives

## Important
- Do NOT ask "Should I proceed?" BEFORE trying a command
- Let Command Guard handle the approval gate
- Only ask AFTER you see APPROVAL_REQUIRED in the tool response

## Approval Request Format
When presenting findings for approval, include:
- Process/file name and what it does
- Resource usage (CPU%, memory) if relevant
- Impact of the action (data loss? can restart?)
- Your recommendation

Example:
```
I found the issue:

**Process:** ffmpeg (PID: 1337)
**Usage:** 95% CPU, 45% Memory
**Task:** Video transcoding
**Impact if killed:** Low - batch job can restart

Should I proceed? Reply 'yes' to approve.
```
