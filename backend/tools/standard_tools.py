import os
import datetime
import time
import psutil
from github import Github
from backend.utils.logger import log_system

# --- MOCK / PRODUCTIVITY TOOLS ---

def send_slack_message(channel: str, message: str):
    """
    Simulates sending a message to a Slack channel.
    
    Args:
        channel: The channel name (e.g., "ops", "general").
        message: The content of the message to send.
    """
    log_system(f"SLACK OUT [{channel}]: {message}", "COMM")
    # In a real app, use slack_sdk.WebClient
    return f"Sent to #{channel}: {message}"

def create_linear_ticket(title: str, priority: str = "Medium"):
    """
    Creates a tracking ticket in Linear (or Jira) for a bug or task.
    
    Args:
        title: The title of the ticket/issue.
        priority: The priority level (Low, Medium, High, Critical).
    """
    ticket_id = f"PROX-{int(time.time()) % 1000}"
    log_system(f"TICKET CREATED [{ticket_id}]: {title} ({priority})", "PM")
    return f"Ticket Created: {ticket_id} | {title}"

def query_knowledge_base(query: str):
    """
    Queries the internal Knowledge Base (RAG) for documentation, runbooks, or procedures.
    Use this when you don't know how to restart a service, deploy, or handle a specific error.
    
    Args:
        query: The search query string.
    """
    log_system(f"Querying Knowledge Base: {query}", "RAG")
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
    """Returns the current server time formatted as YYYY-MM-DD HH:MM:SS."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    """
    Retrieves real-time system metrics (CPU, Memory) from the host machine.
    """
    log_system("Fetching real-time system health metrics...", "SYS")
    try:
        health_data = { 
            "status": "online", 
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        }
        log_system(f"Metrics retrieved: {health_data}", "SYS")
        return health_data
    except Exception as e:
        log_system(f"Error fetching metrics: {e}", "ERR")
        return f"Error getting health: {e}"

# --- GITHUB TOOLS ---

def update_github_file(repo_name: str, file_path: str, content: str):
    """
    Updates (or creates) a file in a GitHub repository.
    
    Args:
        repo_name: The name of the repository (e.g., 'owner/repo').
        file_path: The full path to the file within the repo.
        content: The new text content for the file.
    """
    log_system(f"GitHub: Updating {file_path} in {repo_name}", "GIT")
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
    """
    Creates a new Issue in a GitHub repository.
    
    Args:
        repo_name: The name of the repository.
        title: The issue title.
        body: The detailed description of the issue.
    """
    log_system(f"GitHub: Creating issue '{title}' in {repo_name}", "GIT")
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
