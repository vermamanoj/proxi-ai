import uuid
from backend.database import create_mission_record, add_work_item_record, update_item_status_record
from backend.utils.logger import log_system

# --- ORCHESTRATOR TOOLS FOR LLM ---

def create_mission(goal: str):
    """
    Starts a new long-running mission/research task.
    
    Args:
        goal: The objective of the mission (e.g., "Find 5 React Developers on LinkedIn").
    """
    mission_id = str(uuid.uuid4())[:8]
    create_mission_record(mission_id, goal)
    log_system(f"Mission Started: {goal} (ID: {mission_id})", "ORCHESTRATOR")
    return f"Mission Created. ID: {mission_id}. You can now add items to this mission."

def add_item(mission_id: str, type: str, source: str, attributes: dict):
    """
    Saves a found item (lead, bug, data point) to the mission memory.
    
    Args:
        mission_id: The ID of the current mission.
        type: The category of item (e.g., "LEAD", "BUG", "PR", "ARTICLE").
        source: Where it was found (URL or File Path).
        attributes: A dictionary of extracted data (e.g., {"name": "John", "role": "CTO"}).
    """
    try:
        item_id = add_work_item_record(mission_id, type, source, attributes)
        log_system(f"Item Saved [{type}]: {source}", "ORCHESTRATOR")
        return f"Item saved successfully (ID: {item_id})."
    except Exception as e:
        return f"Error saving item: {e}"

def update_item_status(item_id: int, status: str):
    """
    Updates the status of a work item.
    
    Args:
        item_id: The numeric ID of the item.
        status: New status (APPROVED, REJECTED, PROCESSED).
    """
    update_item_status_record(item_id, status)
    return f"Item {item_id} updated to {status}."
