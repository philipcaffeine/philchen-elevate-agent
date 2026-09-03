# Altostrat Singapore Enterprise HR Agentic Virtual Assistant (MVP 1)

This repository contains the complete implementation of the enterprise-grade **HR Agentic Virtual Assistant** for Altostrat Singapore, built for Google Cloud Vertex AI and Cloud Run, connected to Argolis project **`philchen-project-elevate`**.

Built in accordance with:
- **BRD**: [HR Agentic Solution BRD (MVP 1)](https://docs.google.com/document/d/1B46ERMVZapwSN8RPmsJ0_NnayuUkaTT6ZcujgwdjTX8/edit?resourcekey=0-kwi-DdO3wHIdEk8gtbpeQQ&tab=t.tpcr3esq94y#heading=h.tsvh2037jsz5)
- **SDD**: [`SDD.md`](./SDD.md) ([`ENTERPRISE_AGENTIC_SDD_MVP1.md`](https://github.com/philipcaffeine/gcp-elevate-group3/blob/main/sdd/ENTERPRISE_AGENTIC_SDD_MVP1.md))
- **Elevate APAC Module 3 Tasks**: `go/elevate-apac-m3-policydoc`, `go/elevate-apac-m3-saas`, and `go/elevate-apac-skills`.

---

## 📁 Prescribed Repository Architecture

```text
philchen-elevate-agent/
├── app/                      # Core agent implementation
│   ├── __init__.py
│   ├── agent.py              # ADK LlmAgent / Gemini orchestrator & lifecycle
│   ├── config.py             # Settings, environment variables, model declarations
│   ├── prompt.py             # System prompt with strict grounding, citations & refusal rules
│   ├── guardrails.py         # DLP SPII masking, Model Armor filters, RBAC caller scoping
│   ├── main.py               # Application entrypoint (FastAPI + Web Chat UI)
│   ├── knowledge/            # OKF markdown knowledge base (35 policy sections)
│   └── tools/                # Enterprise connectors and tool functions
│       ├── __init__.py
│       ├── policy_tool.py    # Policy Q&A engine over go/elevate-apac-m3-policydoc
│       ├── hrms_tool.py      # WorkWeek HCM connector (profile, balance, leave, contact)
│       ├── itms_tool.py      # ServiceImmediately ITSM connector via MCP server
│       ├── mcp_client.py     # MCP client handling authorization & token handshake
│       └── workflow_tool.py  # UC-2.2 cross-system medical leave + email delegation
├── tests/                    # Unit and integration test suite
│   ├── __init__.py
│   ├── test_guardrails.py    # Tests for SPII redaction, prompt injection & caller scoping
│   ├── test_tools.py         # Tests for HRMS, ITMS, and Policy retrieval tools
│   └── test_workflows.py     # End-to-end tests for UC-2.2 cross-system transactions
├── eval/                     # Evaluation pipeline
│   ├── datasets/             # Golden test evaluation datasets
│   │   ├── eval-data.json    # Tier 1 & 2 baseline and functional test cases
│   │   └── eval-data2.json   # Tier 3 & 4 edge cases, security traps, and policy gotchas
│   ├── eval_config.yaml      # Metrics, dimensions, weights, and scoring thresholds
│   ├── run_eval.py           # Evaluation runner script
│   └── evaluation_report.md  # 2-section evaluation report (Approach/Design & Results)
├── agents-cli-manifest.yaml  # Google Agents CLI manifest definition
├── pyproject.toml            # Project dependencies and tool configurations
├── Dockerfile                # Cloud Run containerization
├── deploy.sh                 # Deployment script for philchen-project-elevate
└── SDD.md                    # Canonical SDD specification
```

---

## 🚀 Quickstart & Local Execution

### 1. Setup Virtual Environment & Install Dependencies
```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Project is configured for philchen-project-elevate with Gemini 3.5 Flash
```

### 3. Run the Unit Test Suite
```bash
pytest tests/ -v
```

### 4. Run the Evaluation Benchmark
```bash
python eval/run_eval.py
```

### 5. Launch the Local Web Chat Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser to interact with the agent.

---

## ☁️ Deploying to Cloud Run (`philchen-project-elevate`)

Ensure your Google Cloud credentials and project are active:
```bash
gcloud auth login admin@philchen.altostrat.com
gcloud auth application-default login
gcloud config set project philchen-project-elevate

# Deploy to Cloud Run
./deploy.sh
```
