# Quick Tool Reference

## Most Used Tools
- `run_terminal_command` - Execute shell commands
- `look_at_screen` - Screenshot with numbered [N] UI elements
- `ground_and_click` - Find and click UI elements by description
- `share_screenshot` - Show screenshot to user in chat
- `open_target` - Open files, folders, URLs, apps
- `get_system_health` - Check CPU, memory, disk usage

## Macro Actions (Preferred for Efficiency)
- `open_app(app_name)` - Fastest way to launch apps
- `navigate_app(app, destination)` - Open AND navigate in ONE call
- `interact_element(description, action, text)` - Find and interact in ONE call
- `fill_form(fields)` - Fill multiple form fields

## GUI Interaction
1. PREFERRED: `ground_and_click("Submit button")` - auto-finds and clicks
2. ALTERNATIVE: `look_at_screen` first, then `click_at(x, y)` using coordinates

## File Operations
- List desktop: `run_terminal_command("dir $env:USERPROFILE\\Desktop")` (Windows) or `ls ~/Desktop` (Linux)
- Open image: `open_target(image_path)`
- Save uploaded image: `save_uploaded_image(path)`
