
import os
import datetime
import time
import psutil
from github import Github
from backend.utils.logger import log_system

# --- MOCK / PRODUCTIVITY TOOLS ---

def send_slack_message(channel: str, message: str):
    """Simulates sending a message to a Slack channel."""
    log_system(f"SLACK OUT [{channel}]: {message}", "COMM")
    # In a real app, use slack_sdk.WebClient
    return f"Sent to #{channel}: {message}"

def create_linear_ticket(title: str, priority: str = "Medium"):
    """Simulates creating a ticket in Linear/Jira."""
    ticket_id = f"PROX-{int(time.time()) % 1000}"
    log_system(f"TICKET CREATED [{ticket_id}]: {title} ({priority})", "PM")
    return f"Ticket Created: {ticket_id} | {title}"

def query_knowledge_base(query: str):
    """Simulated RAG (Retrieval Augmented Generation)."""
    # Mocking a vector DB lookup logic
    q = query.lower()
    if "restart" in q:
        return "Wiki: To restart the payment service, use `restart_cloud_run_service` with region `us-east1`."
    if "deploy" in q:
        return "Wiki: Deployments require a ticket ID in the commit message."
    if "db" in q or "database" in q:
        return "Wiki: The primary database is Cloud SQL instance 'prod-db-01'."
    return "Wiki: No specific documentation found for this query."

# --- STANDARD SYSTEM TOOLS ---

def get_server_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    try:
        return { 
            "status": "online", 
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent
        }
    except Exception as e:
        return f"Error getting health: {e}"

# --- GITHUB TOOLS ---

def update_github_file(repo_name: str, file_path: str, content: str):
    token = os.getenv("GITHUB_TOKEN")
    if not token: 
        return "Error: GITHUB_TOKEN missing in environment."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            file_content = repo.get_contents(file_path)
            repo.update_file(file_path, "Update via Proxi", content, file_content.sha)
            return f"Updated {file_path}"
        except:
            repo.create_file(file_path, "Create via Proxi", content)
            return f"Created {file_path}"
    except Exception as e:
        return f"GitHub Error: {e}"

def create_github_issue(repo_name: str, title: str, body: str):
    token = os.getenv("GITHUB_TOKEN")
    if not token: 
        return "Error: GITHUB_TOKEN missing."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        return f"Issue Created: {issue.html_url}"
    except Exception as e:
        return f"GitHub Error: {e}"
