import { FunctionDeclaration, Type } from "@google/genai";

export const SYSTEM_INSTRUCTION = `
You are Proxi, a Headless Operator for Google Cloud and GitHub.
Interact via voice.
CRITICAL OUTPUT RULES:
1. **THINK FIRST**: Before using a tool, verbally state your plan briefly (e.g., "I'm checking the logs.").
2. **PLAIN TEXT ONLY**: Do NOT use markdown. No bold (**), italics (*), or code blocks (\`\`\`).
3. **CONCISE**: Keep spoken responses short and direct.
4. **PROTOCOL**: Prefer Shell over GUI. 
   - Use PowerShell 5.1 syntax (use \`;\` instead of \`||\`).
   - If drawing, use \`drag_mouse\` to create shapes.
`;

export const TOOLS: FunctionDeclaration[] = [
  {
    name: "check_github_pr",
    description: "Fetches the status of a specific Pull Request from the active repository.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        pr_number: { type: Type.NUMBER, description: "The PR number to check" },
        repo: { type: Type.STRING, description: "Repository name (optional, defaults to current)" }
      },
      required: ["pr_number"]
    }
  },
  {
    name: "check_gcp_logs",
    description: "Retrieves the latest logs for a specific Google Cloud service.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        service: { type: Type.STRING, description: "The name of the service (e.g., 'auth-service', 'payment-api')" },
        severity: { type: Type.STRING, description: "Log severity level (ERROR, INFO, WARNING)" },
        limit: { type: Type.NUMBER, description: "Number of log lines to retrieve" }
      },
      required: ["service"]
    }
  },
  {
    name: "restart_cloud_run_service",
    description: "Triggers a new revision deployment to restart a Cloud Run service.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        service_name: { type: Type.STRING, description: "Name of the Cloud Run service to restart" },
        region: { type: Type.STRING, description: "GCP Region (default: us-central1)" }
      },
      required: ["service_name"]
    }
  }
];

// Mock data for tools
export const MOCK_GITHUB_DATA = {
  state: "open",
  title: "feat(auth): Add JWT validation middleware",
  author: "jdoe-dev",
  checks: "failing",
  files_changed: 12
};

export const MOCK_LOGS_DATA = (service: string) => [
  `[2024-01-24 10:23:01] INFO  ${service}: Request received POST /v1/init`,
  `[2024-01-24 10:23:02] WARN  ${service}: Latency spike detected (150ms)`,
  `[2024-01-24 10:23:02] ERROR ${service}: Database connection pool exhausted`,
  `[2024-01-24 10:23:03] INFO  ${service}: Retrying connection...`
];