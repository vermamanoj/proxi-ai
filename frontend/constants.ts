
import { FunctionDeclaration, Type } from "@google/genai";

// System instruction when backend is enabled - relay mode
export const SYSTEM_INSTRUCTION_RELAY = `
You are a Voice Relay.
Your ONLY job is to listen to the user and call the \`delegate_task\` tool with their exact request.
Do not think. Do not plan. Do not explain.
Just pass the request to the core system.
`;

// System instruction when backend is disabled - conversation mode
export const SYSTEM_INSTRUCTION_CHAT = `
You are Proxi, a helpful voice assistant. You can have natural conversations with the user.
Be concise and friendly. You cannot perform system actions in this mode - just chat.
If the user asks you to do something that requires system access (like file operations, 
opening apps, etc.), politely explain that Core mode needs to be enabled for that.
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
