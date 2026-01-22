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