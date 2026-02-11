# Proxi — Internal Product Documentation

> **Proxi** is a Headless OS-Level AI Agent that gives users full desktop control from a mobile phone.

---

## Documentation Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [Product Overview](01_overview.md) | Value proposition, target users, tech stack, feature inventory |
| 02 | [Architecture](02_architecture.md) | Three-tier topology, data flow diagrams, component relationships |
| 03 | [Backend Services](03_backend_services.md) | FastAPI Core, Gemini orchestration, session management |
| 04 | [Agent System](04_agent_system.md) | Agent server, desktop service layer, tool execution chain |
| 05 | [Tools Reference](05_tools_reference.md) | Complete catalog of 48+ tools with parameters and examples |
| 06 | [Security](06_security.md) | Authentication, command guardrails, isolation model, threat model |
| 07 | [Prompt Engineering](07_prompt_engineering.md) | System prompt modules, execution modes, assembly pipeline |
| 08 | [Database](08_database.md) | SQLite schema, tables, migrations, data lifecycle |
| 09 | [Deployment](09_deployment.md) | Docker setup, environment variables, requirements, CI/CD |
| 10 | [Developer Guide](10_developer_guide.md) | Local setup, coding conventions, debugging, contributing |
| 11 | [Additional Context](11_additional_context.md) | AI models, frontend versions, demo scenarios, mobile, security history |
| — | [**Onboarding Guide**](ONBOARDING.md) | **Start here** — for new developers and fresh LLM sessions |
| — | [Action Plan](ACTION_PLAN.md) | API audit results, fixes done, features planned for private repo |
| — | [Landing Page Plan](LANDING_PAGE_PLAN.md) | Visual content plan — images, videos, screenshots for homepage |

---

## Quick Links

- **Source Code**: `e:\data\proxi-ai\`
- **Backend Entry**: `backend/main.py` (FastAPI, port 4000/8000)
- **Agent Entry**: `backend/agent_server.py` (FastAPI, port 8081)
- **Frontend Entry**: `frontend/App.tsx` (React+Vite, port 4002)
- **Docker Compose**: `docker-compose.yml`

## Conventions Used

- File references use relative paths from repo root (e.g., `backend/main.py`)
- Code excerpts are illustrative — always check source for current implementation
- `[CORE]` = Proxi Core server, `[AGENT]` = Proxi Agent server, `[FE]` = Frontend

---

*Last updated: February 2026*
