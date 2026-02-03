/**
 * Static Workstation Configuration (Frontend Fallback)
 * 
 * This provides workstation data when backend is unavailable.
 * The frontend will attempt to fetch from backend API first,
 * falling back to this static config if backend is unreachable.
 */

export type WorkstationType = 'container' | 'vm' | 'physical' | 'mock';
export type WorkstationStatus = 'online' | 'offline' | 'starting' | 'unknown' | 'error';

export interface Workstation {
  id: string;
  name: string;
  description: string;
  type: WorkstationType;
  host: string;
  port: number;
  capabilities: string[];
  status: WorkstationStatus;
  tags: string[];
  isDefault?: boolean;
}

/**
 * Default workstations - used when backend is unavailable
 * These should match the backend registry for consistency
 */
export const DEFAULT_WORKSTATIONS: Workstation[] = [
  {
    id: 'linux-container',
    name: 'Linux Agent (Always On)',
    description: 'Docker container on Oracle Ubuntu - terminal, git, python automation',
    type: 'container',
    host: '127.0.0.1',
    port: 8081,
    capabilities: ['terminal', 'git', 'python', 'docker', 'file_operations'],
    status: 'unknown', // Will be updated by health check
    tags: ['linux', 'always-on'],
    isDefault: true,
  },
  {
    id: 'windows-vm',
    name: 'Windows Desktop (On-Demand)',
    description: 'Windows Server 2022 via Tailscale - GUI automation, Office, legacy apps',
    type: 'vm',
    host: '100.100.100.2', // Tailscale IP - update after setup
    port: 8081,
    capabilities: ['desktop', 'mouse', 'keyboard', 'screenshot', 'powerpoint', 'browser'],
    status: 'unknown',
    tags: ['windows', 'on-demand', 'gui'],
    isDefault: false,
  },
];

/**
 * Get workstation by ID from static config
 */
export function getStaticWorkstation(id: string): Workstation | undefined {
  return DEFAULT_WORKSTATIONS.find(w => w.id === id);
}

/**
 * Get default workstation from static config
 */
export function getDefaultWorkstation(): Workstation {
  return DEFAULT_WORKSTATIONS.find(w => w.isDefault) || DEFAULT_WORKSTATIONS[0];
}
