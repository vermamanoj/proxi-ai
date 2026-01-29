#!/usr/bin/env python3
"""
Fake Crypto-Miner Simulation
Simulates NCvhHaev malware behavior for SOC training
"""

import os
import sys
import time
import socket
import threading
import signal

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown"""
    global running
    print("\n[MINER] Received shutdown signal...")
    running = False
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def cpu_load():
    """Simulate High CPU Usage (consumes ~90-100% of 1 core)"""
    print("[MINER] Starting CPU load simulation...")
    iteration = 0
    while running:
        # CPU-intensive computation
        _ = [x**2 for x in range(50000)]
        iteration += 1
        # Brief sleep to allow system responsiveness
        time.sleep(0.0001)
        
        # Periodic status (every ~10 seconds)
        if iteration % 10000 == 0:
            print(f"[MINER] CPU load active... iterations: {iteration}")

def network_connection():
    """
    Simulate connection to Mining Pool
    Attempts to connect to 119.28.183.120:19999 (fake C2/pool)
    Connection will fail but show in netstat as SYN_SENT or similar
    """
    print("[MINER] Attempting connection to mining pool...")
    while running:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            # Try to connect to non-existent mining pool
            # This will hang or fail, creating forensic evidence in netstat
            sock.connect(('119.28.183.120', 19999))
            print("[MINER] Connected to mining pool (unexpected!)")
            time.sleep(30)
        except socket.timeout:
            print("[MINER] Connection timeout (expected - pool unreachable)")
            time.sleep(10)
        except socket.error as e:
            print(f"[MINER] Connection failed: {e} (expected)")
            time.sleep(10)
        except Exception as e:
            print(f"[MINER] Network error: {e}")
            time.sleep(10)
        finally:
            try:
                sock.close()
            except:
                pass

def fake_postgres():
    """
    FALSE LEAD: Simulate PostgreSQL listening on localhost
    This makes analysts think DB might be attack vector
    """
    print("[DB] Starting fake PostgreSQL on 0.0.0.0:5432...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 5432))
        sock.listen(1)
        print("[DB] PostgreSQL simulation listening on 0.0.0.0:5432")
        
        while running:
            time.sleep(100)
    except OSError as e:
        print(f"[DB] Could not bind to port 5432: {e}")
        print("[DB] Port may already be in use - skipping DB simulation")
    except Exception as e:
        print(f"[DB] Error: {e}")

def rename_process():
    """
    Attempt to rename the process to 'NCvhHaev'
    This is visible in ps/top output
    """
    try:
        # Copy self to /tmp with malware name
        script_path = os.path.abspath(__file__)
        malware_path = '/tmp/NCvhHaev'
        
        # Note: In Docker, this may not fully hide the process
        # but will create the suspicious binary name
        if not os.path.exists(malware_path):
            import shutil
            shutil.copy(script_path, malware_path)
            os.chmod(malware_path, 0o755)
            print(f"[MINER] Created malware binary: {malware_path}")
        
        # Try to modify process name (limited effectiveness in Python)
        # Real malware would use C/assembly for this
        sys.argv[0] = './NCvhHaev'
        
    except Exception as e:
        print(f"[MINER] Process rename failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("CRYPTO-MINER SIMULATION STARTED")
    print("=" * 60)
    print(f"PID: {os.getpid()}")
    print(f"User: {os.getuid()}")
    print("This is a SIMULATION for SOC training purposes")
    print("=" * 60)
    
    # Rename process to look like malware
    rename_process()
    
    # Start fake PostgreSQL (false lead)
    db_thread = threading.Thread(target=fake_postgres, daemon=True)
    db_thread.start()
    
    # Start fake mining pool connection
    net_thread = threading.Thread(target=network_connection, daemon=True)
    net_thread.start()
    
    # Give threads time to start
    time.sleep(2)
    
    print("\n[MINER] All systems operational. Starting CPU load...")
    print("[MINER] Use 'top' or 'ps' to observe this process")
    print("[MINER] Use 'netstat -antp' to see network connections")
    print("=" * 60 + "\n")
    
    # Main CPU load (blocking)
    try:
        cpu_load()
    except KeyboardInterrupt:
        print("\n[MINER] Interrupted by user")
        running = False
    except Exception as e:
        print(f"\n[MINER] Fatal error: {e}")
        running = False
    
    print("[MINER] Shutdown complete")
