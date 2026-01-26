"""
Workstation Registry for Proxi

Manages registered backend workstations that Proxi can connect to.
Supports multiple workstations with different capabilities.
"""

import json
import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum


class WorkstationType(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    CONTAINER = "container"


class WorkstationStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class WorkstationCapability:
    name: str
    description: str
    available: bool = True


@dataclass
class Workstation:
    id: str
    name: str
    description: str
    workstation_type: str  # WorkstationType value
    host: str  # IP or hostname (Tailscale IP for private)
    port: int = 8080
    capabilities: List[str] = field(default_factory=list)
    status: str = "unknown"  # WorkstationStatus value
    last_seen: str = ""
    created_at: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        return f"{self.api_url}/api/health"


class WorkstationRegistry:
    """
    Registry for managing Proxi backend workstations.
    """
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or self._default_config_file()
        self.workstations: Dict[str, Workstation] = {}
        self._load_workstations()
    
    def _default_config_file(self) -> str:
        """Get default path for workstations config file."""
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir / "registry" / "workstations.json")
    
    def _load_workstations(self):
        """Load workstations from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for ws_id, ws_data in data.items():
                        self.workstations[ws_id] = Workstation(**ws_data)
            except Exception as e:
                print(f"[REGISTRY] Error loading workstations: {e}")
        else:
            # Create default demo workstations
            self._create_demo_workstations()
    
    def _save_workstations(self):
        """Save workstations to JSON file."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        data = {ws_id: ws.to_dict() for ws_id, ws in self.workstations.items()}
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _create_demo_workstations(self):
        """Create demo workstations for hackathon."""
        demo_workstations = [
            Workstation(
                id="linux-container",
                name="Linux Agent (Always On)",
                description="Docker container on Oracle Ubuntu - terminal, git, python automation",
                workstation_type=WorkstationType.CONTAINER.value,
                host="127.0.0.1",  # Local container on same server
                port=8081,
                capabilities=[
                    "terminal",
                    "git",
                    "python",
                    "docker",
                    "file_operations"
                ],
                status=WorkstationStatus.ONLINE.value,  # Always on
                created_at=datetime.utcnow().isoformat(),
                owner="demo",
                tags=["demo", "linux", "always-on"]
            ),
            Workstation(
                id="sales-win-vm",
                name="Sales Demo Workstation",
                description="Windows Server with CRM, Pricing Tool, and Office applications",
                workstation_type=WorkstationType.WINDOWS.value,
                host="100.100.100.2",  # Tailscale IP - update after setup
                port=8080,
                capabilities=[
                    "desktop_automation",
                    "screenshot",
                    "browser",
                    "powerpoint",
                    "crm",
                    "pricing_tool"
                ],
                status=WorkstationStatus.OFFLINE.value,
                created_at=datetime.utcnow().isoformat(),
                owner="demo",
                tags=["demo", "sales", "windows"]
            ),
            Workstation(
                id="finance-desktop",
                name="Finance Desktop",
                description="Windows 11 with Excel, SAP, and financial applications",
                workstation_type=WorkstationType.WINDOWS.value,
                host="100.100.100.4",
                port=8080,
                capabilities=[
                    "desktop_automation",
                    "excel",
                    "sap",
                    "quickbooks"
                ],
                status=WorkstationStatus.OFFLINE.value,
                created_at=datetime.utcnow().isoformat(),
                owner="demo",
                tags=["demo", "finance", "windows"]
            ),
            Workstation(
                id="devops-container",
                name="DevOps Container",
                description="Docker container with CI/CD and monitoring tools",
                workstation_type=WorkstationType.CONTAINER.value,
                host="100.100.100.5",
                port=8080,
                capabilities=[
                    "terminal",
                    "kubernetes",
                    "prometheus",
                    "grafana"
                ],
                status=WorkstationStatus.OFFLINE.value,
                created_at=datetime.utcnow().isoformat(),
                owner="demo",
                tags=["demo", "devops", "container"]
            ),
        ]
        
        for ws in demo_workstations:
            self.workstations[ws.id] = ws
        
        self._save_workstations()
        print(f"[REGISTRY] Created demo workstations in {self.config_file}")
    
    def list_workstations(self, owner: str = None) -> List[Workstation]:
        """List all workstations, optionally filtered by owner."""
        workstations = list(self.workstations.values())
        if owner:
            workstations = [ws for ws in workstations if ws.owner == owner]
        return workstations
    
    def get_workstation(self, workstation_id: str) -> Optional[Workstation]:
        """Get a workstation by ID."""
        return self.workstations.get(workstation_id)
    
    def register_workstation(self, workstation: Workstation) -> Workstation:
        """Register a new workstation."""
        workstation.created_at = datetime.utcnow().isoformat()
        workstation.status = WorkstationStatus.UNKNOWN.value
        self.workstations[workstation.id] = workstation
        self._save_workstations()
        return workstation
    
    def update_workstation(self, workstation_id: str, updates: dict) -> Optional[Workstation]:
        """Update a workstation's properties."""
        ws = self.workstations.get(workstation_id)
        if not ws:
            return None
        
        for key, value in updates.items():
            if hasattr(ws, key):
                setattr(ws, key, value)
        
        self._save_workstations()
        return ws
    
    def delete_workstation(self, workstation_id: str) -> bool:
        """Delete a workstation."""
        if workstation_id in self.workstations:
            del self.workstations[workstation_id]
            self._save_workstations()
            return True
        return False
    
    async def check_workstation_health(self, workstation_id: str, timeout: int = 5) -> WorkstationStatus:
        """Check if a workstation is online by calling its health endpoint."""
        ws = self.workstations.get(workstation_id)
        if not ws:
            return WorkstationStatus.UNKNOWN
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ws.health_url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 200:
                        ws.status = WorkstationStatus.ONLINE.value
                        ws.last_seen = datetime.utcnow().isoformat()
                        self._save_workstations()
                        return WorkstationStatus.ONLINE
                    else:
                        ws.status = WorkstationStatus.ERROR.value
                        self._save_workstations()
                        return WorkstationStatus.ERROR
        except asyncio.TimeoutError:
            ws.status = WorkstationStatus.OFFLINE.value
            self._save_workstations()
            return WorkstationStatus.OFFLINE
        except Exception as e:
            print(f"[REGISTRY] Health check failed for {workstation_id}: {e}")
            ws.status = WorkstationStatus.ERROR.value
            self._save_workstations()
            return WorkstationStatus.ERROR
    
    async def check_all_health(self) -> Dict[str, WorkstationStatus]:
        """Check health of all registered workstations."""
        results = {}
        tasks = []
        
        for ws_id in self.workstations:
            tasks.append(self.check_workstation_health(ws_id))
        
        statuses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ws_id, status in zip(self.workstations.keys(), statuses):
            if isinstance(status, Exception):
                results[ws_id] = WorkstationStatus.ERROR
            else:
                results[ws_id] = status
        
        return results
    
    def get_active_workstation(self) -> Optional[Workstation]:
        """Get the first online workstation."""
        for ws in self.workstations.values():
            if ws.status == WorkstationStatus.ONLINE.value:
                return ws
        return None


# Singleton instance
_registry: WorkstationRegistry = None


def get_registry() -> WorkstationRegistry:
    """Get the singleton WorkstationRegistry instance."""
    global _registry
    if _registry is None:
        _registry = WorkstationRegistry()
    return _registry


# API helper functions
def list_workstations(owner: str = None) -> List[dict]:
    """List all workstations as dicts."""
    registry = get_registry()
    return [ws.to_dict() for ws in registry.list_workstations(owner)]


def get_workstation(workstation_id: str) -> Optional[dict]:
    """Get a workstation by ID as dict."""
    registry = get_registry()
    ws = registry.get_workstation(workstation_id)
    return ws.to_dict() if ws else None


async def get_workstation_status(workstation_id: str) -> dict:
    """Get workstation status with health check."""
    registry = get_registry()
    status = await registry.check_workstation_health(workstation_id)
    ws = registry.get_workstation(workstation_id)
    
    return {
        "id": workstation_id,
        "status": status.value,
        "last_seen": ws.last_seen if ws else None,
        "api_url": ws.api_url if ws else None
    }


def get_active_backend_url() -> Optional[str]:
    """Get the API URL of the first active backend."""
    registry = get_registry()
    ws = registry.get_active_workstation()
    return ws.api_url if ws else None
