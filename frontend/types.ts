
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
    step_type: 'user_input' | 'llm_plan' | 'tool_call' | 'tool_result' | 'final_response';
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

export type Complexity = 'fast' | 'deep';

export type AgentStatus = 'idle' | 'processing' | 'speaking' | 'analyzing_visuals' | 'awaiting_confirmation';

export interface PendingAction {
  type: string;
  description: string;
  data: any;
}