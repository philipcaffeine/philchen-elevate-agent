"""Application configuration for Enterprise HR Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Project & Model
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "philchen-project-elevate")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.6-flash")

# SaaS / MCP Server
SAAS_MCP_SERVER_URL = os.getenv("SAAS_MCP_SERVER_URL", "https://mock-saas.aishprabhat.demo.altostrat.com/")
SAAS_MCP_TOKEN = os.getenv("SAAS_MCP_TOKEN", "mcp_Is3gTPFDZb3NCbOXYakrtGHqsDVwf6gcbuIJpvEU1zs")
SIMULATE_MCP = os.getenv("SIMULATE_MCP", "false").lower() == "true"

# Audit & Governance Headers
ORIGIN_HEADER_VALUE = "Altostrat-HR-Agent-MVP1"

# Paths
KNOWLEDGE_DIR = ROOT_DIR / "app" / "knowledge"
if not KNOWLEDGE_DIR.exists():
    KNOWLEDGE_DIR = ROOT_DIR / "knowledge"

# Server
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")
APP_NAME = "altostrat-hr-agent"
