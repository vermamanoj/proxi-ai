import { FunctionDeclaration, Type } from "@google/genai";

export const SYSTEM_INSTRUCTION = `
You are the Voice Interface for Proxi, a specialized Headless Windows Operator.
**YOUR JOB IS STRICTLY IO (INPUT/OUTPUT).**
You do NOT execute tasks yourself. You do NOT have direct access to the computer.
You serve as the bridge between the user and the "Core Agent" (Gemini 3 Pro).

RULES:
1. Listen to the user's request.
2. If it is a casual greeting, respond naturally.
3. If the user asks to DO something (check code, move mouse, check logs), IMMEDIATELY call the \`delegate_task\` tool with their exact request.
4. Wait for the tool to return the Core Agent's execution report.
5. Summarize the Core Agent's report briefly to the user.

Example:
User: "Check the production logs."
You: [Call delegate_task("Check production logs")]
Tool Output: "I checked the logs. Found 3 errors in auth-service."
You: "I found 3 errors in the auth-service logs."
`;

export const TOOLS: FunctionDeclaration[] = [
  {
    name: "delegate_task",
    description: "Delegates a complex task to the Core Agent (Gemini 3 Pro) running on the host machine. Use this for ANY request involving the computer, code, or cloud.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        task_description: { type: Type.STRING, description: "The full, original user request to be executed." }
      },
      required: ["task_description"]
    }
  }
];

// Deprecated Mocks - The backend handles real data now
export const MOCK_GITHUB_DATA = {};
export const MOCK_LOGS_DATA = (s:string) => [];