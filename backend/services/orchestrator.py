import uuid
import json
import psutil
import requests
import base64
from backend.database import (
    create_mission_record, 
    add_work_item_record, 
    update_item_status_record, 
    update_mission_verification,
    get_mission_record
)
from backend.services.desktop.factory import get_desktop_service
from backend.utils.logger import log_system

# --- TRIPLE HANDSHAKE WORKFLOW ---

def assign_mission(goal: str, verification_criteria: str = "{}"):
    """
    Starts a new verifiable mission.
    
    Args:
        goal: The objective (e.g., "Restore service health").
        verification_criteria: JSON string defining success metrics. Examples:
            - '{"metric": "cpu", "threshold": 50, "condition": "less_than"}'
            - '{"metric": "http", "url": "http://localhost:8080/health", "expected_status": 200}'
    """
    # Parse JSON string to dict
    try:
        criteria_dict = json.loads(verification_criteria) if isinstance(verification_criteria, str) else verification_criteria
    except json.JSONDecodeError:
        criteria_dict = {}
    
    mission_id = str(uuid.uuid4())[:8]
    create_mission_record(mission_id, goal, criteria_dict)
    log_system(f"Mission Assigned: {goal} (ID: {mission_id})", "ORCHESTRATOR")
    return f"Mission {mission_id} assigned. Criteria: {json.dumps(criteria_dict)}"

def report_execution(mission_id: str, summary: str):
    """
    Worker Agent calls this to report it has finished the task.
    """
    log_system(f"Execution Report [{mission_id}]: {summary}", "WORKER")
    update_mission_verification(mission_id, "PENDING_VERIFICATION", summary)
    return "Report received. Initiating Independent Verification..."

def verify_mission(mission_id: str):
    """
    INDEPENDENTLY checks system state against the mission's criteria.
    Returns the system metrics (Evidence) for the Verifier Agent to judge.
    """
    mission = get_mission_record(mission_id)
    if not mission:
        return json.dumps({"error": "Mission not found"})
    
    try:
        criteria = json.loads(mission.get('verification_criteria', '{}'))
    except:
        criteria = {}

    log_system(f"Verifying Mission {mission_id} against criteria: {criteria}", "VERIFIER")
    
    evidence = {}
    verification_type = criteria.get("type", criteria.get("metric"))  # Support both new and legacy format
    
    # 1. Process Killed Check (supports both "process_killed" and "process_exists" formats)
    if verification_type in ["process_killed", "process_exists"]:
        pid = criteria.get("pid")
        if pid:
            try:
                # Check if process still exists
                process_exists = psutil.pid_exists(int(pid))
                evidence["pid"] = pid
                evidence["process_exists"] = process_exists
                
                # For process_killed or process_exists with condition "is_false"/"false" - expect NOT running
                expect_gone = (verification_type == "process_killed" or 
                              criteria.get("condition") in ["is_false", "false", False])
                
                if expect_gone:
                    if process_exists:
                        finalize_mission(mission_id, "FAILED")
                        return json.dumps({"fail_reason": f"Process {pid} still running.", "evidence": evidence})
                    else:
                        finalize_mission(mission_id, "PASSED")
                        return json.dumps({"status": "VERIFICATION PASSED", "message": f"Process {pid} confirmed terminated.", "evidence": evidence})
                else:
                    # Expect process to be running
                    if not process_exists:
                        finalize_mission(mission_id, "FAILED")
                        return json.dumps({"fail_reason": f"Process {pid} not running.", "evidence": evidence})
                    else:
                        finalize_mission(mission_id, "PASSED")
                        return json.dumps({"status": "VERIFICATION PASSED", "message": f"Process {pid} confirmed running.", "evidence": evidence})
            except Exception as e:
                evidence["error"] = str(e)
    
    # 2. File Exists Check (NEW - for action verification)
    if verification_type == "file_exists":
        import os
        path = criteria.get("path")
        should_exist = criteria.get("should_exist", True)
        if path:
            exists = os.path.exists(path)
            evidence["path"] = path
            evidence["exists"] = exists
            if exists != should_exist:
                finalize_mission(mission_id, "FAILED")
                return json.dumps({"fail_reason": f"File {path} {'exists' if exists else 'does not exist'}, expected {'to exist' if should_exist else 'to not exist'}.", "evidence": evidence})
            else:
                finalize_mission(mission_id, "PASSED")
                return json.dumps({"status": "VERIFICATION PASSED", "message": f"File check passed for {path}.", "evidence": evidence})
    
    # 3. Service Status Check (NEW)
    if verification_type == "service_stopped" or verification_type == "service_running":
        service_name = criteria.get("service")
        expected_running = (verification_type == "service_running")
        # This would need platform-specific implementation
        evidence["service"] = service_name
        evidence["check_type"] = verification_type
    
    # 4. Legacy CPU Check (kept for backwards compatibility but should not be used for transient metrics)
    if verification_type == "cpu":
        ds = get_desktop_service()
        health = ds.get_system_health()
        cpu = health.get("cpu_percent", psutil.cpu_percent(interval=1))
        
        evidence["cpu"] = cpu
        threshold = criteria.get("threshold", 100)
        if criteria.get("condition") == "less_than" and cpu > threshold:
             finalize_mission(mission_id, "FAILED")
             return json.dumps({"fail_reason": f"CPU is {cpu}%, expected < {threshold}%."})

    # 5. HTTP Check
    if criteria.get("metric") == "http":
        url = criteria.get("url")
        try:
            res = requests.get(url, timeout=5)
            evidence["http_status"] = res.status_code
            evidence["http_body_snippet"] = res.text[:200]
            if res.status_code != criteria.get("expected_status", 200):
                finalize_mission(mission_id, "FAILED")
                return json.dumps({"fail_reason": f"{url} returned {res.status_code}."})
        except Exception as e:
            evidence["http_error"] = str(e)
            finalize_mission(mission_id, "FAILED")
            return json.dumps({"fail_reason": f"Could not reach {url}. Error: {e}"})

    # 3. Visual Check
    if criteria.get("metric") == "visual":
        try:
            ds = get_desktop_service()
            screenshot = ds.get_screenshot_base64()
            if screenshot:
                evidence["screenshot_base64"] = screenshot
                evidence["visual_target"] = criteria.get("description", "Check screen state")
            else:
                evidence["visual_error"] = "Failed to capture screenshot"
        except Exception as e:
            evidence["visual_error"] = str(e)

    # 4. Default System Vitals
    ds = get_desktop_service()
    evidence["system_vitals"] = ds.get_system_health()
    
    return json.dumps(evidence)

def finalize_mission(mission_id: str, status: str):
    """Updates the mission status in the DB."""
    update_mission_verification(mission_id, status)
    log_system(f"Mission {mission_id} Finalized: {status}", "VERIFIER")

def escalate_to_human(mission_id: str, reason: str):
    """
    Triggers when the Agent gets stuck or fails verification repeatedly.
    """
    log_system(f"ESCALATION [{mission_id}]: {reason}", "CRITICAL")
    finalize_mission(mission_id, "ESCALATED")
    # In a real app, this would PageDuty/Email
    return f"Mission {mission_id} ESCALATED to Human Operator. Reason: {reason}"

# --- LEGACY / HELPER TOOLS ---

def create_mission(goal: str):
    return assign_mission(goal, {})

def add_item(mission_id: str, type: str, source: str, attributes: dict):
    try:
        item_id = add_work_item_record(mission_id, type, source, attributes)
        return f"Item saved successfully (ID: {item_id})."
    except Exception as e:
        return f"Error saving item: {e}"

def update_item_status(item_id: int, status: str):
    update_item_status_record(item_id, status)
    return f"Item {item_id} updated to {status}."
