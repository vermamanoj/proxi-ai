
export enum MessageSource {
  USER = 'USER',
  SYSTEM = 'SYSTEM',
  AGENT = 'AGENT',
  TOOL = 'TOOL'
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  source: MessageSource;
  text: string;
  metadata?: any;
}

export interface TraceStep {
    step_type: 'user_input' | 'llm_thought' | 'tool_call' | 'tool_result' | 'final_response' | 'system_instruction' | 'verification' | 'status_change' | 'agent_switch';
    content: string | any;
    metadata?: any;
}

export interface ToolCall {
  name: string;
  args: any;
  status: 'running' | 'completed' | 'failed';
  result?: any;
}

export interface ActiveToolState {
  name: string;
  startTime: number;
}

export type Complexity = 'quick' | 'balanced' | 'thorough' | 'fast' | 'deep';  // fast/deep are legacy mappings

export type AgentStatus = 'idle' | 'processing' | 'speaking' | 'analyzing_visuals' | 'awaiting_confirmation';

export interface PendingAction {
  type: string;
  description: string;
  data: any;
}

export type ApprovalType = 'binary' | 'choice' | 'freeform' | 'confirm_screenshot';

export interface ApprovalRequest {
  id: string;
  type: ApprovalType;
  title: string;
  description: string;
  options?: string[];
  screenshotUrl?: string;
  placeholder?: string;
  timeoutSeconds?: number;
  metadata?: any;
}

export type MissionPhase = 'idle' | 'listening' | 'planning' | 'executing' | 'verifying' | 'success' | 'failed' | 'stalled';

export interface VerificationState {
    status: 'pending' | 'checking' | 'success' | 'failed';
    reason?: string;
}

export interface MissionState {
    active: boolean;
    phase: MissionPhase;
    goal: string;
    activeTool?: string;
    verification: VerificationState;
    retryCount: number;
}
