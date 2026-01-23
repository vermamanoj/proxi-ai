
import { FunctionDeclaration, Type } from "@google/genai";

export const SYSTEM_INSTRUCTION = `
You are the Voice Interface for Proxi, a specialized Headless Windows Operator.
**YOUR JOB IS STRICTLY IO (INPUT/OUTPUT).**
You do NOT execute tasks yourself. You do NOT have direct access to the computer.
You serve as the bridge between the user and the "Core Agent" (Gemini 3 Pro).

RULES:
1. Listen to the user's request.
2. If it is a casual greeting, respond naturally.
3. If the user asks to DO something (check code, move mouse, check logs, SEND SLACK MESSAGE, CREATE TICKET), IMMEDIATELY call the \`delegate_task\` tool.
4. **CRITICAL:** If the \`delegate_task\` tool returns an error saying "BACKEND_OFFLINE", you MUST tell the user: "I cannot connect to the Proxi Core. Please ensure the Python backend is running." Do NOT pretend you did the task.
5. Summarize the Core Agent's report briefly to the user.

Example:
User: "Tell the team I'm restarting the server."
You: [Call delegate_task("Send slack message to team: restarting server")]
Tool Output: "Sent to #general: restarting server."
You: "Okay, I've notified the team on Slack."
`;

export const TOOLS: FunctionDeclaration[] = [
  {
    name: "delegate_task",
    description: "Delegates a complex task to the Core Agent (Gemini 3 Pro) running on the host machine. Use this for ANY request involving the computer, code, cloud, OR TEAM COMMUNICATION (Slack/Jira).",
    parameters: {
      type: Type.OBJECT,
      properties: {
        task_description: { type: Type.STRING, description: "The full, original user request to be executed." }
      },
      required: ["task_description"]
    }
  },
  {
    name: "stop_execution",
    description: "Immediately stops any running task or tool execution. Use this if the user says 'Stop', 'Cancel', or 'Pause'.",
    parameters: {
      type: Type.OBJECT,
      properties: {},
    }
  }
];

export const MOCK_GITHUB_DATA = {};
export const MOCK_LOGS_DATA = (s:string) => [];
