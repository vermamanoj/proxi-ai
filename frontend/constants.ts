
import { FunctionDeclaration, Type } from "@google/genai";

export const SYSTEM_INSTRUCTION = `
You are a Voice Relay.
Your ONLY job is to listen to the user and call the \`delegate_task\` tool with their exact request.
Do not think. Do not plan. Do not explain.
Just pass the request to the core system.
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
