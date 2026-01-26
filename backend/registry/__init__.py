"""
Workstation Registry module for Proxi
"""
from .workstation_registry import (
    WorkstationRegistry,
    Workstation,
    WorkstationType,
    WorkstationStatus,
    get_registry,
    list_workstations,
    get_workstation,
    get_workstation_status,
    get_active_backend_url
)

__all__ = [
    'WorkstationRegistry',
    'Workstation',
    'WorkstationType',
    'WorkstationStatus',
    'get_registry',
    'list_workstations',
    'get_workstation',
    'get_workstation_status',
    'get_active_backend_url'
]
