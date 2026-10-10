# Haven

A privacy-first, AI-powered platform for proactive burnout detection and organizational insights using behavioral metadata.

## Overview

Haven detects employee burnout proactively from behavioral metadata while maintaining privacy-first principles and providing AI-driven actionable insights. It moves away from surveillance-heavy monitoring and point-in-time surveys to provide a continuous, privacy-preserving solution.

## Key Features

- **Proactive Burnout Detection:** Uses behavioral metadata (GitHub, Slack, Google Calendar) to identify risk before it happens.
- **Privacy by Design:** Two-vault database architecture ensuring zero PII in the analytics database.
- **Talent Discovery:** Identifies hidden organizational talent through network centrality analysis.
- **Team Contagion Modeling:** Models team-level burnout spread using epidemiological math (SIR model).
- **AI-Powered Insights:** Multi-agent chat system (powered by Gemini 2.5 Flash) for conversational HR insights.

## Tech Stack

- **Backend:** FastAPI 0.139.0 (Python 3.14.6), PostgreSQL (Supabase), Redis
- **Frontend:** Next.js 16.2.10 (React 19.2.7), Tailwind CSS, Recharts
- **AI & Analytics:** Google Gemini 3.5 Flash, SciPy, NetworkX
- **Infrastructure:** Docker, Composio MCP

## Documentation

For a more detailed breakdown of the architecture, methodologies, database schemas, and project scope, please refer to the [Project Overview](./personal%20documentations/haven_project_overview.md).
