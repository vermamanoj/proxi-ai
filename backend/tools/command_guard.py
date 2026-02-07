"""
Command Guard - OS Command Security Guardrails for Proxi

This module provides security checks for terminal commands before execution.
It blocks dangerous commands and requires approval for sensitive operations.
"""

import re
from typing import Tuple, List
from dataclasses import dataclass
from enum import Enum


class CommandRisk(Enum):
    SAFE = "safe"
    NEEDS_APPROVAL = "needs_approval"
    BLOCKED = "blocked"


@dataclass
class CommandCheckResult:
    allowed: bool
    risk_level: CommandRisk
    reason: str
    matched_pattern: str = ""


# Commands that are ALWAYS blocked - too dangerous
BLOCKED_PATTERNS: List[Tuple[str, str]] = [
    # Destructive file operations
    (r'rm\s+-rf\s+/', "Recursive delete from root"),
    (r'rm\s+-rf\s+\*', "Recursive delete wildcard"),
    (r'del\s+/[sS]\s+/[qQ]\s+[cC]:', "Windows recursive delete C:"),
    (r'rd\s+/[sS]\s+/[qQ]\s+[cC]:', "Windows remove directory C:"),
    (r'format\s+[a-zA-Z]:', "Format drive"),
    (r'mkfs\.', "Make filesystem"),
    (r'dd\s+if=.+of=/dev/', "Direct disk write"),
    
    # System destruction
    (r'shutdown\s+(-h|-r|/s|/r)', "System shutdown/reboot"),
    (r'reboot', "System reboot"),
    (r'halt', "System halt"),
    (r'init\s+[06]', "Init level change"),
    (r'systemctl\s+(poweroff|reboot|halt)', "Systemd power control"),
    
    # Fork bombs and resource exhaustion
    (r':\(\)\s*{\s*:\|:&\s*};\s*:', "Bash fork bomb"),
    (r'%0\|%0', "Windows fork bomb"),
    
    # Credential/security bypass
    (r'passwd\s+root', "Change root password"),
    (r'net\s+user\s+administrator', "Modify administrator"),
    (r'chmod\s+777\s+/', "Chmod 777 root"),
    (r'chmod\s+-R\s+777', "Recursive chmod 777"),
    
    # Registry destruction (Windows)
    (r'reg\s+delete\s+HKLM', "Delete HKLM registry"),
    (r'reg\s+delete\s+HKCR', "Delete HKCR registry"),
    
    # Boot/system config
    (r'bcdedit\s+/delete', "Delete boot entry"),
    (r'bcdedit\s+/set', "Modify boot config"),
    (r'grub-install', "Modify bootloader"),
    
    # Disk/partition operations
    (r'fdisk\s+/dev/', "Partition editing"),
    (r'diskpart', "Windows disk partitioning"),
    (r'parted', "Partition editing"),
    
    # Network attacks
    (r'iptables\s+-F', "Flush firewall rules"),
    (r'netsh\s+advfirewall\s+set\s+.*\s+state\s+off', "Disable Windows firewall"),
]

# Commands that require user approval before execution
APPROVAL_REQUIRED_PATTERNS: List[Tuple[str, str]] = [
    # Package installation
    (r'pip\s+install', "Python package installation"),
    (r'pip3\s+install', "Python package installation"),
    (r'npm\s+install\s+-g', "Global npm package installation"),
    (r'apt\s+install', "APT package installation"),
    (r'apt-get\s+install', "APT package installation"),
    (r'yum\s+install', "YUM package installation"),
    (r'choco\s+install', "Chocolatey package installation"),
    (r'winget\s+install', "Winget package installation"),
    
    # Process termination
    (r'Stop-Process', "PowerShell stop process"),
    (r'taskkill', "Windows task kill"),
    (r'kill\s+-9', "Force kill process"),
    (r'pkill', "Kill processes by name"),
    (r'killall', "Kill all matching processes"),
    
    # Service control
    (r'net\s+stop', "Stop Windows service"),
    (r'net\s+start', "Start Windows service"),
    (r'sc\s+stop', "Stop service"),
    (r'sc\s+delete', "Delete service"),
    (r'systemctl\s+stop', "Stop systemd service"),
    (r'systemctl\s+disable', "Disable systemd service"),
    
    # File deletion (non-recursive)
    (r'Remove-Item', "PowerShell remove item"),
    (r'rm\s+(?!-rf)', "Remove file"),
    (r'del\s+', "Windows delete"),
    (r'unlink', "Unlink file"),
    
    # User/permission changes
    (r'useradd', "Add user"),
    (r'userdel', "Delete user"),
    (r'net\s+user\s+\w+\s+/add', "Add Windows user"),
    (r'chmod\s+', "Change permissions"),
    (r'chown\s+', "Change ownership"),
    (r'icacls', "Windows permissions"),
    
    # Network changes
    (r'netsh\s+interface', "Network interface config"),
    (r'route\s+(add|delete)', "Routing table change"),
    (r'iptables\s+', "Firewall rule change"),
    
    # Scheduled tasks
    (r'schtasks\s+/create', "Create scheduled task"),
    (r'schtasks\s+/delete', "Delete scheduled task"),
    (r'crontab\s+', "Cron job modification"),
    (r'^at\s+\d', "AT job scheduling"),  # Only match 'at' command with time argument
    
    # Environment changes
    (r'setx\s+', "Set environment variable permanently"),
    (r'export\s+PATH=', "Modify PATH"),
    
    # Database operations
    (r'DROP\s+(DATABASE|TABLE)', "SQL drop operation"),
    (r'TRUNCATE\s+TABLE', "SQL truncate"),
    (r'DELETE\s+FROM\s+\w+\s*;', "SQL delete all"),
]

# Commands that are generally safe
# Note: patterns use (\s|$) to match command with args OR standalone
SAFE_PATTERNS: List[Tuple[str, str]] = [
    (r'^ls(\s|$)', "List directory"),
    (r'^ll(\s|$)', "List directory long"),
    (r'^dir(\s|$)', "Windows list directory"),
    (r'^cat(\s|$)', "View file"),
    (r'^type(\s|$)', "Windows view file"),
    (r'^Get-Content', "PowerShell get content"),
    (r'^echo(\s|$)', "Echo text"),
    (r'^Write-Output', "PowerShell write output"),
    (r'^pwd$', "Print working directory"),
    (r'^Get-Location', "PowerShell get location"),
    (r'^whoami', "Current user"),
    (r'^hostname', "Hostname"),
    (r'^date', "Current date"),
    (r'^Get-Date', "PowerShell get date"),
    (r'^uptime', "System uptime"),
    (r'^df(\s|$)', "Disk free"),
    (r'^free(\s|$)', "Memory free"),
    (r'^top(\s|$)', "Process list"),
    (r'^htop(\s|$)', "Process list"),
    (r'^ps(\s|$)', "Process status"),
    (r'^Get-Process', "PowerShell get process"),
    (r'^netstat', "Network statistics"),
    (r'^ipconfig', "IP configuration"),
    (r'^ifconfig', "Interface configuration"),
    (r'^ip\s+(addr|link|route)', "IP config"),
    (r'^ping(\s|$)', "Ping host"),
    (r'^curl(\s|$)', "HTTP request"),
    (r'^wget(\s|$)', "Download file"),
    (r'^Invoke-WebRequest', "PowerShell web request"),
    (r'^head(\s|$)', "View file head"),
    (r'^tail(\s|$)', "View file tail"),
    (r'^grep(\s|$)', "Search text"),
    (r'^awk(\s|$)', "Text processing"),
    (r'^sed(\s|$)', "Stream editor"),
    (r'^Select-String', "PowerShell search"),
    (r'^find(\s|$)', "Find files"),
    (r'^which(\s|$)', "Find command path"),
    (r'^whereis(\s|$)', "Find binary"),
    (r'^Get-ChildItem', "PowerShell list"),
    (r'^wc(\s|$)', "Word count"),
    (r'^sort(\s|$)', "Sort text"),
    (r'^uniq(\s|$)', "Unique lines"),
    (r'^env$', "Environment variables"),
    (r'^printenv', "Print environment"),
    (r'^\$env:', "PowerShell env variable"),
    (r'^cd(\s|$)', "Change directory"),
    (r'^Set-Location', "PowerShell change dir"),
    (r'^mkdir(\s|$)', "Make directory"),
    (r'^touch(\s|$)', "Create empty file"),
    (r'^cp(\s|$)', "Copy file"),
    (r'^mv(\s|$)', "Move file"),
    (r'^history', "Command history"),
    (r'^man(\s|$)', "Manual page"),
    (r'^help', "Help"),
    (r'^Get-Help', "PowerShell help"),
    (r'^less(\s|$)', "Page through file"),
    (r'^more(\s|$)', "Page through file"),
    (r'^tree(\s|$)', "Directory tree"),
    (r'^clear$', "Clear screen"),
    (r'^cls$', "Clear screen"),
    (r'^stat(\s|$)', "File status"),
    (r'^file(\s|$)', "File type"),
    (r'^id$', "User ID info"),
    (r'^groups', "User groups"),
    (r'^uname', "System info"),
    (r'^lsb_release', "Distribution info"),
    (r'^systeminfo', "Windows system info"),
    (r'^journalctl', "View system logs"),
    (r'^ss(\s|$)', "Socket statistics"),
    (r'^lsof', "List open files"),
    (r'^strace', "System trace"),
    (r'^strings(\s|$)', "Extract strings"),
    (r'^xxd(\s|$)', "Hex dump"),
    (r'^hexdump', "Hex dump"),
    (r'^md5sum', "MD5 checksum"),
    (r'^sha256sum', "SHA256 checksum"),
    (r'^docker\s+(ps|images|logs|inspect)', "Docker read-only"),
    (r'^git\s+(status|log|diff|branch|show|remote)', "Git read-only"),
    (r'npm\s+(list|ls|view|info|search)', "NPM read-only"),
    (r'pip\s+(list|show|freeze)', "Pip read-only"),  # Matches ./venv/bin/pip too
    (r'pip3\s+(list|show|freeze)', "Pip3 read-only"),
    (r'python3?\s+-c\s+["\']import', "Python import check"),  # Read-only import test
    (r'^python\s+--version', "Python version"),
    (r'^python3\s+--version', "Python3 version"),
    (r'^pip3?\s+--version', "Pip version"),
    (r'^node\s+--version', "Node version"),
    (r'^npm\s+--version', "NPM version"),
    (r'^java\s+--version', "Java version"),
    (r'^go\s+version', "Go version"),
    (r'^ruby\s+--version', "Ruby version"),
    (r'^cargo\s+--version', "Cargo version"),
    (r'^rustc\s+--version', "Rust version"),
    (r'^dotnet\s+--version', "Dotnet version"),
    (r'--version$', "Version check (any tool)"),
    (r'-v$', "Version check short"),
    (r'-V$', "Version check short"),
    
    # Windows-specific safe commands for Proxi demo
    (r'^start\s+', "Windows start command"),
    (r'^Start-Process', "PowerShell start process"),
    (r'^Invoke-Item', "PowerShell open file/shortcut"),
    (r'^explorer\.exe', "Windows explorer"),
    (r'^New-Object\s+-ComObject', "PowerShell COM object"),
    (r'^Get-CimInstance', "PowerShell CIM query"),
    (r'^Get-WmiObject', "PowerShell WMI query"),
    (r'\.lnk["\']?\s*$', "Open shortcut file"),
    (r'^cmd\s+/c', "CMD wrapper"),
    (r'MinimizeAll', "Minimize windows"),
    (r'^Get-ItemProperty', "PowerShell registry read"),
    (r'^Test-Path', "PowerShell path test"),
    (r'^Resolve-Path', "PowerShell resolve path"),
    (r'^Split-Path', "PowerShell split path"),
    (r'^Join-Path', "PowerShell join path"),
    (r'CreateShortcut', "Read shortcut target"),
    (r'WScript\.Shell', "WScript shell object"),
    (r'Select-Object', "PowerShell select"),
    (r'Where-Object', "PowerShell where filter"),
    (r'ForEach-Object', "PowerShell foreach"),
    (r'Format-Table', "PowerShell format"),
    (r'Format-List', "PowerShell format"),
    (r'Out-String', "PowerShell output"),
    (r'MainWindowTitle', "Get window title"),
    (r'^Get-Item\s', "PowerShell get item"),
]


class CommandGuard:
    """
    Security guard for terminal command execution.
    Checks commands against blocked, approval-required, and safe patterns.
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize CommandGuard.
        
        Args:
            strict_mode: If True, unknown commands require approval.
                        If False, unknown commands are allowed.
        """
        self.strict_mode = strict_mode
        self.blocked_patterns = BLOCKED_PATTERNS
        self.approval_patterns = APPROVAL_REQUIRED_PATTERNS
        self.safe_patterns = SAFE_PATTERNS
    
    def check_command(self, command: str) -> CommandCheckResult:
        """
        Check if a command is safe to execute.
        
        Args:
            command: The shell command to check
            
        Returns:
            CommandCheckResult with allowed status, risk level, and reason
        """
        command = command.strip()
        
        # Check blocked patterns first (highest priority)
        for pattern, description in self.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return CommandCheckResult(
                    allowed=False,
                    risk_level=CommandRisk.BLOCKED,
                    reason=f"BLOCKED: {description}",
                    matched_pattern=pattern
                )
        
        # Check safe patterns FIRST (before approval patterns)
        # This prevents broad approval patterns from matching safe commands
        for pattern, description in self.safe_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return CommandCheckResult(
                    allowed=True,
                    risk_level=CommandRisk.SAFE,
                    reason=f"Safe command: {description}",
                    matched_pattern=pattern
                )
        
        # Check approval required patterns
        for pattern, description in self.approval_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return CommandCheckResult(
                    allowed=True,
                    risk_level=CommandRisk.NEEDS_APPROVAL,
                    reason=f"Requires approval: {description}",
                    matched_pattern=pattern
                )
        
        # Unknown command - depends on strict mode
        if self.strict_mode:
            return CommandCheckResult(
                allowed=True,
                risk_level=CommandRisk.NEEDS_APPROVAL,
                reason="Unknown command - requires approval in strict mode",
                matched_pattern=""
            )
        else:
            return CommandCheckResult(
                allowed=True,
                risk_level=CommandRisk.SAFE,
                reason="Unknown command - allowed in permissive mode",
                matched_pattern=""
            )
    
    def add_blocked_pattern(self, pattern: str, description: str):
        """Add a custom blocked pattern."""
        self.blocked_patterns.append((pattern, description))
    
    def add_approval_pattern(self, pattern: str, description: str):
        """Add a custom approval-required pattern."""
        self.approval_patterns.append((pattern, description))
    
    def add_safe_pattern(self, pattern: str, description: str):
        """Add a custom safe pattern."""
        self.safe_patterns.append((pattern, description))


# ============================================================================
# FILE OPERATION GUARDRAILS
# ============================================================================

# Protected paths - NEVER allow delete/overwrite
PROTECTED_PATHS: List[str] = [
    # Windows system paths
    r'C:\\Windows',
    r'C:\\Program Files',
    r'C:\\Program Files \(x86\)',
    r'C:\\ProgramData',
    r'C:\\Users\\.*\\AppData\\Local\\Microsoft',
    r'C:\\Users\\.*\\NTUSER\.DAT',
    
    # Linux system paths
    r'^/etc/',
    r'^/usr/',
    r'^/bin/',
    r'^/sbin/',
    r'^/boot/',
    r'^/lib/',
    r'^/var/log/',
    r'^/root/',
    
    # Git and version control
    r'\.git/',
    r'\.svn/',
    r'\.hg/',
    
    # Sensitive files
    r'\.env$',
    r'\.env\.',
    r'\.pem$',
    r'\.key$',
    r'\.crt$',
    r'id_rsa',
    r'id_ed25519',
    r'\.ssh/',
    r'credentials',
    r'secrets\..*',
]

# File extensions that require approval before modification
SENSITIVE_EXTENSIONS: List[str] = [
    '.exe', '.dll', '.sys', '.msi',  # Windows executables
    '.sh', '.bash', '.zsh',          # Shell scripts
    '.ps1', '.bat', '.cmd',          # Windows scripts
    '.pem', '.key', '.crt', '.p12',  # Certificates/keys
    '.db', '.sqlite', '.mdb',        # Databases
    '.conf', '.config', '.ini',      # Config files
    '.reg',                          # Registry files
]


@dataclass
class FileCheckResult:
    allowed: bool
    risk_level: CommandRisk
    reason: str
    path: str = ""


class FileGuard:
    """
    Security guard for file operations.
    Prevents deletion/modification of protected paths.
    """
    
    def __init__(self):
        self.protected_paths = PROTECTED_PATHS
        self.sensitive_extensions = SENSITIVE_EXTENSIONS
    
    def check_path(self, path: str, operation: str = "access") -> FileCheckResult:
        """
        Check if a file operation is safe.
        
        Args:
            path: The file path to check
            operation: Type of operation (read, write, delete, execute)
            
        Returns:
            FileCheckResult with safety information
        """
        path_normalized = path.replace('/', '\\') if '\\' in path else path
        
        # Check protected paths
        for protected in self.protected_paths:
            if re.search(protected, path, re.IGNORECASE):
                if operation in ['delete', 'write', 'overwrite']:
                    return FileCheckResult(
                        allowed=False,
                        risk_level=CommandRisk.BLOCKED,
                        reason=f"Protected path - {operation} not allowed",
                        path=path
                    )
                elif operation == 'read':
                    return FileCheckResult(
                        allowed=True,
                        risk_level=CommandRisk.SAFE,
                        reason="Protected path - read only",
                        path=path
                    )
        
        # Check sensitive extensions for write/delete
        if operation in ['delete', 'write', 'overwrite', 'execute']:
            for ext in self.sensitive_extensions:
                if path.lower().endswith(ext):
                    return FileCheckResult(
                        allowed=True,
                        risk_level=CommandRisk.NEEDS_APPROVAL,
                        reason=f"Sensitive file type ({ext}) - requires approval",
                        path=path
                    )
        
        # Default: allow with appropriate risk level
        if operation == 'delete':
            return FileCheckResult(
                allowed=True,
                risk_level=CommandRisk.NEEDS_APPROVAL,
                reason="File deletion requires approval",
                path=path
            )
        elif operation in ['write', 'overwrite']:
            return FileCheckResult(
                allowed=True,
                risk_level=CommandRisk.NEEDS_APPROVAL,
                reason="File modification requires approval",
                path=path
            )
        else:
            return FileCheckResult(
                allowed=True,
                risk_level=CommandRisk.SAFE,
                reason="File operation allowed",
                path=path
            )
    
    def check_delete(self, path: str) -> FileCheckResult:
        """Check if a file can be deleted."""
        return self.check_path(path, "delete")
    
    def check_write(self, path: str) -> FileCheckResult:
        """Check if a file can be written/overwritten."""
        return self.check_path(path, "write")
    
    def check_execute(self, path: str) -> FileCheckResult:
        """Check if a file can be executed."""
        return self.check_path(path, "execute")


# ============================================================================
# PRIVILEGE ESCALATION DETECTION
# ============================================================================

PRIVILEGE_ESCALATION_PATTERNS: List[Tuple[str, str]] = [
    # Linux privilege escalation
    (r'sudo\s+su\s*$', "Switch to root user"),
    (r'sudo\s+-i', "Interactive root shell"),
    (r'sudo\s+bash', "Root bash shell"),
    (r'su\s+-\s*$', "Switch to root"),
    (r'pkexec', "PolicyKit execution"),
    
    # Windows privilege escalation
    (r'runas\s+/user:administrator', "Run as administrator"),
    (r'Start-Process.*-Verb\s+RunAs', "PowerShell elevate"),
    (r'net\s+localgroup\s+administrators.*\/add', "Add to administrators"),
    (r'secedit', "Security policy edit"),
    
    # Capability/permission changes
    (r'setcap', "Set capabilities"),
    (r'setfacl', "Set ACLs"),
    (r'visudo', "Edit sudoers"),
]


def check_privilege_escalation(command: str) -> CommandCheckResult:
    """
    Check if a command attempts privilege escalation.
    
    Args:
        command: The command to check
        
    Returns:
        CommandCheckResult indicating if escalation detected
    """
    for pattern, description in PRIVILEGE_ESCALATION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return CommandCheckResult(
                allowed=False,
                risk_level=CommandRisk.BLOCKED,
                reason=f"Privilege escalation blocked: {description}",
                matched_pattern=pattern
            )
    
    return CommandCheckResult(
        allowed=True,
        risk_level=CommandRisk.SAFE,
        reason="No privilege escalation detected",
        matched_pattern=""
    )


# ============================================================================
# SINGLETON INSTANCES
# ============================================================================

_guard_instance: CommandGuard = None
_file_guard_instance: FileGuard = None


def get_command_guard(strict_mode: bool = True) -> CommandGuard:
    """Get the singleton CommandGuard instance."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = CommandGuard(strict_mode=strict_mode)
    return _guard_instance


def check_command_safety(command: str) -> CommandCheckResult:
    """
    Convenience function to check command safety.
    
    Args:
        command: The shell command to check
        
    Returns:
        CommandCheckResult with safety information
    """
    return get_command_guard().check_command(command)


def get_file_guard() -> FileGuard:
    """Get the singleton FileGuard instance."""
    global _file_guard_instance
    if _file_guard_instance is None:
        _file_guard_instance = FileGuard()
    return _file_guard_instance


def check_file_safety(path: str, operation: str = "access") -> FileCheckResult:
    """
    Convenience function to check file operation safety.
    
    Args:
        path: The file path to check
        operation: Type of operation (read, write, delete, execute)
        
    Returns:
        FileCheckResult with safety information
    """
    return get_file_guard().check_path(path, operation)


def full_security_check(command: str, file_paths: List[str] = None) -> dict:
    """
    Perform comprehensive security check on command and file paths.
    
    Args:
        command: The command to check
        file_paths: Optional list of file paths involved
        
    Returns:
        Dict with overall safety assessment
    """
    results = {
        "allowed": True,
        "risk_level": "safe",
        "reasons": [],
        "command_check": None,
        "file_checks": [],
        "privilege_check": None
    }
    
    # Check command
    cmd_result = check_command_safety(command)
    results["command_check"] = {
        "allowed": cmd_result.allowed,
        "risk": cmd_result.risk_level.value,
        "reason": cmd_result.reason
    }
    
    if not cmd_result.allowed:
        results["allowed"] = False
        results["risk_level"] = "blocked"
        results["reasons"].append(cmd_result.reason)
    elif cmd_result.risk_level == CommandRisk.NEEDS_APPROVAL:
        results["risk_level"] = "needs_approval"
        results["reasons"].append(cmd_result.reason)
    
    # Check privilege escalation
    priv_result = check_privilege_escalation(command)
    results["privilege_check"] = {
        "allowed": priv_result.allowed,
        "risk": priv_result.risk_level.value,
        "reason": priv_result.reason
    }
    
    if not priv_result.allowed:
        results["allowed"] = False
        results["risk_level"] = "blocked"
        results["reasons"].append(priv_result.reason)
    
    # Check file paths if provided
    if file_paths:
        file_guard = get_file_guard()
        for path in file_paths:
            # Determine operation from command
            operation = "access"
            if any(p in command.lower() for p in ['rm ', 'del ', 'remove', 'delete']):
                operation = "delete"
            elif any(p in command.lower() for p in ['>', 'write', 'set-content', 'out-file']):
                operation = "write"
            
            file_result = file_guard.check_path(path, operation)
            results["file_checks"].append({
                "path": path,
                "allowed": file_result.allowed,
                "risk": file_result.risk_level.value,
                "reason": file_result.reason
            })
            
            if not file_result.allowed:
                results["allowed"] = False
                results["risk_level"] = "blocked"
                results["reasons"].append(f"{path}: {file_result.reason}")
            elif file_result.risk_level == CommandRisk.NEEDS_APPROVAL:
                if results["risk_level"] != "blocked":
                    results["risk_level"] = "needs_approval"
                results["reasons"].append(f"{path}: {file_result.reason}")
    
    return results


# Example usage and testing
if __name__ == "__main__":
    guard = CommandGuard()
    
    test_commands = [
        # Safe commands
        "ls -la",
        "Get-Process",
        "ping google.com",
        "cat /etc/hosts",
        
        # Approval required
        "pip install requests",
        "taskkill /F /IM notepad.exe",
        "rm myfile.txt",
        "net stop spooler",
        
        # Blocked commands
        "rm -rf /",
        "format C:",
        "shutdown -h now",
        ":(){ :|:& };:",
        "reg delete HKLM\\SOFTWARE",
    ]
    
    print("Command Guard Test Results:")
    print("=" * 60)
    
    for cmd in test_commands:
        result = guard.check_command(cmd)
        status = "✅" if result.allowed else "❌"
        risk = result.risk_level.value.upper()
        print(f"{status} [{risk:15}] {cmd[:40]:40} | {result.reason}")
