import { FunctionDeclaration, Type } from "@google/genai";

// API Base URL - empty for same-origin, or set for cross-origin
export const API_BASE = import.meta.env.VITE_API_URL || '';

// System instruction when backend is enabled - relay mode
export const SYSTEM_INSTRUCTION_RELAY = `
You are a Voice Relay.
Your ONLY job is to listen to the user and call the \`delegate_task\` tool with their exact request.
Do not think. Do not plan. Do not explain.
Just pass the request to the core system.
`;

// System instruction when backend is disabled - conversation mode
export const SYSTEM_INSTRUCTION_CHAT = `
You are Proxi, a friendly voice assistant. Respond naturally and conversationally.
Keep responses brief and direct - this is voice, not text.
Do NOT output your thinking process or internal reasoning.
Do NOT use markdown formatting like **bold** or headers.
Just speak naturally as if talking to a friend.
If asked to perform system actions (files, apps, commands), say "Enable Core mode for that."
`;

export const TOOLS: FunctionDeclaration[] = [
  {
    name: "delegate_task",
    description: "Send the user's request to the Core System.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        task_description: { type: Type.STRING, description: "The exact request from the user." }
      },
      required: ["task_description"]
    }
  },
  {
    name: "stop_execution",
    description: "Stop the current task.",
    parameters: {
      type: Type.OBJECT,
      properties: {},
    }
  }
];

export const MOCK_GITHUB_DATA = {};
export const MOCK_LOGS_DATA = (s:string) => [];
