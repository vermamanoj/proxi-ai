# 07 — Prompt Engineering

## Overview

Proxi uses a **modular prompt assembly system** where the LLM's system instruction is built dynamically from external Markdown template files based on the selected execution mode. This allows prompt tuning without code changes and mode-specific behavior.

Key files:
- `backend/config/modes.json` — Defines execution modes with model, limits, and prompt section lists
- `backend/config/prompts/*.md` — Individual prompt modules
- `backend/services/gemini_service.py` — `_build_system_prompt()` assembler

---

## Execution Modes (`modes.json`)

Each mode configures the model, conversation limits, and which prompt modules to include:

```json
{
  "modes": {
    "plan": {
      "display_name": "Plan 📋",
      "model": "flash",
      "max_turns": 3,
      "max_tool_calls": 0,
      "timeout": 30,
      "verify": false,
      "include_sections": ["base", "mission_planning"]
    },
    "quick": {
      "display_name": "Quick ⚡",
      "model": "flash",
      "max_turns": 8,
      "max_tool_calls": 12,
      "timeout": 45,
      "verify": false,
      "include_sections": ["base", "command_guard", "tools_quick_ref"]
    },
    "balanced": {
      "display_name": "Balanced ⚖️",
      "model": "flash",
      "max_turns": 10,
      "max_tool_calls": 20,
      "timeout": 60,
      "verify": "auto",
      "include_sections": ["base", "mission_planning", "command_guard", "verifiable_agent", "tools_quick_ref"]
    },
    "thorough": {
      "display_name": "Thorough 🔬",
      "model": "pro",
      "max_turns": 15,
      "max_tool_calls": 40,
      "timeout": 90,
      "verify": true,
      "include_sections": ["base", "mission_planning", "command_guard", "verifiable_agent", "tools_quick_ref", "powerpoint", "forensics"]
    }
  },
  "global": {
    "session_history_size": 50
  }
}
```

> **Model mapping in code** (`gemini_service.py`): `"flash"` → `gemini-3-flash-preview`, `"pro"` → `gemini-3-pro-preview`. Vision analysis also uses `gemini-3-flash-preview`. Image generation uses `gemini-3-pro-image-preview`.

### Mode Comparison

| Mode | Model | Tools | Turns | Timeout | Verification | Use Case |
|------|-------|-------|-------|---------|-------------|----------|
| **plan** | Flash | 0 | 3 | 30s | No | Planning only, no execution |
| **quick** | Flash | 12 | 8 | 45s | No | Simple queries, single-action tasks |
| **balanced** | Flash | 20 | 10 | 60s | Auto | Standard operations, multi-step tasks |
| **thorough** | Pro | 40 | 15 | 90s | Yes | Complex investigations, PPT creation |

### Mode Selection Logic

The frontend sends the mode name with each chat request. The mode determines:
1. Which Gemini model variant to use
2. How many tool calls the LLM can make before being cut off
3. How many conversational turns are allowed
4. Whether Triple Handshake verification is enabled
5. Which prompt sections are loaded

---

## Prompt Modules

### Module: `base.md`

**Always included.** Establishes Proxi's core identity and behavioral rules.

#### Content Summary

```markdown
# Proxi - Headless OS Operator

You are Proxi, a Headless Operator with FULL OS-level access on this {agent_os} computer.

## Expertise
- Windows: PowerShell, Registry, Services, Event Viewer, Task Manager
- Linux: Bash, systemd, journalctl, top/htop, networking
- Security: Log analysis, process forensics, incident response
- Automation: Desktop GUI control, file management, application scripting

## System Context
- Connected to: {agent_os} system
- Shell: {shell_type}
- Mode: {mode} (max {max_tool_calls} tool calls, {timeout}s timeout)

## Core Behavior
### Think Before Acting
Before EVERY tool call, explain: WHAT you're doing, WHY, and WHAT you expect.

### Window Management
Before clicking, typing, or analyzing any application window:
1. Call focus_window(title)
2. Wait briefly
3. Then proceed

### CLI Over GUI
{windows_cli_tips}

### Tool Limits
If task requires more than {max_tool_calls} tool calls, inform user and suggest higher mode.

## Output Rules
- ALWAYS end with a human-readable summary
- NEVER end with just a tool call
- Include relevant details for informed decisions
```

#### Template Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{agent_os}` | Active agent's platform | `Windows`, `Linux` |
| `{shell_type}` | Derived from OS | `PowerShell`, `Bash` |
| `{mode}` | Selected mode name | `balanced` |
| `{max_tool_calls}` | Mode config | `20` |
| `{timeout}` | Mode config | `60` |
| `{prompt_suffix}` | Additional context | Agent capabilities |
| `{windows_cli_tips}` | OS-specific CLI guidance | PowerShell tips for Windows |

---

### Module: `verifiable_agent.md`

**Included in**: balanced, thorough

Guides the LLM on when (and when not) to use the Triple Handshake verification pattern.

```markdown
# Verifiable Agent Protocol

Use Triple Handshake ONLY for STATE-CHANGING ACTIONS that can be verified.

## When TO Use (action tasks with persistent results)
- "Kill process X" → verify process no longer exists
- "Delete file Y" → verify file is gone
- "Stop service Z" → verify service stopped

## When NOT To Use (query tasks with transient results)
- "Check CPU usage" → just call get_system_health and report
- "List processes" → just run command and report results
These metrics change every second - verification would always fail!

## Triple Handshake Steps
1. assign_mission(goal, verification_criteria)
2. Execute the action
3. report_execution(mission_id, summary)
```

**Key insight**: Without this module, the LLM would try to verify every task (including read-only queries), causing false verification failures for transient metrics.

---

### Module: `mission_planning.md`

**Included in**: balanced, thorough

Teaches the LLM to output structured plans that the frontend can parse and display as progress trackers.

```markdown
# Mission Planning

For ANY request with 2+ steps, output a structured plan IMMEDIATELY:

MISSION: [4-5 word summary]
PLAN_START
G1: [4-5 word goal] - [one line description]
G2: [4-5 word goal] - [one line description]
PLAN_END

## Progress Updates (CRITICAL)
Before starting a goal:   GOAL_UPDATE: G1 ACTIVE
After completing a goal:   GOAL_UPDATE: G1 COMPLETE - [brief result]
```

**Frontend integration**: The SSE handler parses `PLAN_START/PLAN_END` blocks and `GOAL_UPDATE` lines to render a visual progress tracker showing completed/active/pending goals.

---

### Module: `command_guard.md`

**Included in**: balanced, thorough

Explains the approval flow from the LLM's perspective so it doesn't pre-ask for permission.

```markdown
# Command Guard Protocol

## How It Works
1. Execute commands directly - don't pre-ask for approval
2. If command needs approval, run_terminal_command returns APPROVAL_REQUIRED:...
3. Tell user what needs approval and ask "Should I proceed?"
4. When user says "yes": Retry the SAME command
5. BLOCKED commands: Inform user and suggest alternatives

## Important
- Do NOT ask "Should I proceed?" BEFORE trying a command
- Let Command Guard handle the approval gate
```

**Key insight**: Without this module, the LLM would ask "Should I kill the process?" before even trying, creating unnecessary friction. The guard system is designed to be transparent — just execute and handle the response.

---

### Module: `tools_quick_ref.md`

**Included in**: quick, balanced, thorough

Concise reference for the most commonly used tools and preferred patterns.

```markdown
# Quick Tool Reference

## Most Used Tools
- run_terminal_command - Execute shell commands
- look_at_screen - Screenshot with numbered [N] UI elements
- ground_and_click - Find and click UI elements by description
- share_screenshot - Show screenshot to user in chat
- open_target - Open files, folders, URLs, apps

## Macro Actions (Preferred for Efficiency)
- open_app(app_name) - Fastest way to launch apps
- navigate_app(app, destination) - Open AND navigate in ONE call
- interact_element(description, action, text) - Find and interact in ONE call

## GUI Interaction
1. PREFERRED: ground_and_click("Submit button") - auto-finds and clicks
2. ALTERNATIVE: look_at_screen first, then click_at(x, y)
```

---

### Module: `workflows/forensics.md`

**Included in**: thorough

Specialized workflow for security incident investigation.

```markdown
# Forensic Investigation Workflow

## Incident Resolution Flow
1. DIAGNOSE: Check system health, identify the problem
2. ANALYZE: Identify specific process (name, PID, resource usage)
3. EXECUTE: Run the command - Command Guard will intercept if needed
4. VERIFY: Check system health again to confirm resolution
5. CONFIRM: Report the final outcome

## Evidence Pattern
- store_evidence(claim, type, data) - Store evidence as you find it
- list_evidence() - Show user what's available
- get_evidence(id) - Retrieve specific evidence on request

## Attack Path Visualization
- render_attack_path(title, stages, annotations) - Generate visual diagram

## Process Investigation Commands
- Windows: Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
- Linux: ps aux --sort=-%cpu | head -10
```

---

### Module: `workflows/powerpoint.md`

**Included in**: thorough

Structured workflow for PowerPoint creation/editing.

```markdown
# PowerPoint Workflow

## 1. ANALYZE PHASE
- ppt_get_active_presentation() to check if already open
- ppt_get_theme_colors() to understand colors and fonts
- ppt_get_slide_info(0) to see all slides

## 2. PLAN PHASE
- Structure content (titles, key points, flow)
- Decide which reference slide to duplicate

## 3. BUILD PHASE
- ppt_duplicate_slide() - clone a reference slide
- ppt_edit_text() - replace content preserving formatting
- ppt_add_table(), ppt_add_chart() - data elements
- ppt_add_image_from_url(), ppt_add_icon() - visual elements

## 4. VERIFY PHASE
- ppt_goto_slide() and look_at_screen() to visually verify
- ppt_save_presentation() when complete

TIP: Duplicate existing slides rather than creating blank ones
```

---

## Prompt Assembly Pipeline

### `_build_system_prompt()` in `gemini_service.py`

```python
def _build_system_prompt(self, mode_config, agent_os, agent_id):
    sections = mode_config.get("prompt_sections", ["base"])
    prompt_parts = []

    for section in sections:
        # Try direct path first, then workflows/ subfolder
        for path_template in [
            f"backend/config/prompts/{section}.md",
            f"backend/config/prompts/workflows/{section}.md"
        ]:
            if os.path.exists(path_template):
                template = open(path_template).read()
                rendered = template.format(
                    agent_os=agent_os,
                    shell_type="PowerShell" if "windows" in agent_os.lower() else "Bash",
                    mode=mode_name,
                    max_tool_calls=mode_config["max_tool_calls"],
                    timeout=mode_config["timeout"],
                    prompt_suffix=self._get_prompt_suffix(agent_id),
                    windows_cli_tips=self._get_cli_tips(agent_os),
                )
                prompt_parts.append(rendered)
                break

    return "\n\n".join(prompt_parts)
```

### Runtime Context Injection

In addition to system prompt, each user message is prefixed with agent context:

```python
context_prefix = f"[CURRENT AGENT: {agent_os} - use {shell_type} commands]"
full_message = f"{context_prefix}\n\n{user_message}"
```

This ensures the LLM always knows which OS/shell to target, even mid-conversation after an agent switch.

---

## Voice Mode Modifiers

When the user's message starts with specific prefixes, a behavioral modifier is injected:

| Prefix | Modifier Prompt |
|--------|----------------|
| `explain:` | "Provide a detailed explanation with context and reasoning" |
| `investigate:` | "Conduct a thorough investigation, gathering evidence systematically" |
| `prove:` | "Verify claims with evidence, run tests, show proof" |
| `summarize:` | "Provide a brief, structured summary of findings" |

These are detected in `route_and_execute_stream()` before the message is sent to Gemini.

---

## Prompt Design Principles

### 1. Transparency Before Action
The base prompt requires the LLM to explain WHAT, WHY, and WHAT IT EXPECTS before every tool call. This creates an audit trail and builds user trust.

### 2. CLI Over GUI
The prompt explicitly prioritizes terminal commands over GUI automation, since CLI commands are more reliable, faster, and deterministic.

### 3. Progressive Disclosure
- **plan mode**: Minimal prompt, no tools — just think
- **quick mode**: Basic tools, quick reference
- **balanced mode**: Full toolset with verification and guardrails
- **thorough mode**: Everything including specialized workflows

### 4. Structured Output Parsing
`PLAN_START/PLAN_END` and `GOAL_UPDATE` markers are designed for machine parsing by the SSE handler, enabling the frontend to render visual progress trackers without complex NLP.

### 5. Graceful Degradation
Tool limit warnings in the base prompt teach the LLM to inform users early if a task needs more tools than the current mode allows, suggesting a mode upgrade.

---

## Adding New Prompt Modules

1. Create a new `.md` file in `backend/config/prompts/` (or `prompts/workflows/` for domain-specific workflows)
2. Use `{template_variables}` for dynamic content
3. Add the module name to relevant mode entries in `modes.json`
4. Test with each mode to ensure the prompt doesn't exceed context limits

**Example**: Adding a "data_analysis" workflow:

```markdown
# backend/config/prompts/workflows/data_analysis.md

# Data Analysis Workflow

## 1. INGEST
- Identify data source (CSV, database, API)
- Use run_terminal_command to inspect file structure

## 2. ANALYZE
- Use Python/pandas for computation
- Store intermediate results

## 3. VISUALIZE
- Generate charts if PowerPoint is available
- Share key findings with user
```

Then in `modes.json`, add `"workflows/data_analysis"` to the thorough mode's `prompt_sections` array.

---

*Previous: [Security ←](06_security.md) | Next: [Database →](08_database.md)*
