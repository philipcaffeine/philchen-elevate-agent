"""FastAPI Application & Web Chat UI for Altostrat HR Agent."""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import config
from .agent import run_agent_turn
from .tools import (
    get_employee_profile,
    get_leave_balances,
    get_incident_ticket,
    list_concepts,
)
from .guardrails import redact_spii

app = FastAPI(
    title="Altostrat Singapore HR Agentic Virtual Assistant",
    description="Enterprise HR Virtual Assistant for Policy Q&A, WorkWeek HCM, and ServiceImmediately ITSM.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str
    caller_id: Optional[str] = "EMP1024"
    session_id: Optional[str] = "web-session-1"


@app.get("/healthz")
async def health_check():
    """Liveness probe for Cloud Run."""
    return {"status": "healthy", "service": "altostrat-hr-agent", "version": "1.0.0"}


@app.get("/api/profile/{employee_id}")
async def api_profile(employee_id: str):
    profile = get_employee_profile(employee_id)
    if profile.get("status_code") != 200:
        raise HTTPException(status_code=profile.get("status_code", 400), detail=profile.get("error"))
    return profile


@app.get("/api/balances/{employee_id}")
async def api_balances(employee_id: str):
    bal = get_leave_balances(employee_id)
    if bal.get("status_code") != 200:
        raise HTTPException(status_code=bal.get("status_code", 400), detail=bal.get("error"))
    return bal


@app.get("/api/tickets/{ticket_id}")
async def api_ticket(ticket_id: str):
    t = get_incident_ticket(ticket_id)
    if t.get("status_code") != 200:
        raise HTTPException(status_code=t.get("status_code", 400), detail=t.get("error"))
    return t


@app.get("/api/concepts")
async def api_concepts():
    return list_concepts()


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Main conversational endpoint interfacing with ADK and Guardrails."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = await run_agent_turn(
        message=req.message,
        caller_id=req.caller_id or "EMP1024",
        session_id=req.session_id or "default-session",
    )
    return result


@app.get("/", response_class=HTMLResponse)
async def web_chat_client():
    """Interactive Enterprise Web Chat UI."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Altostrat HR Virtual Assistant</title>
    <style>
        :root {
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --primary: #1a73e8;
            --primary-hover: #1557b0;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --user-bubble: #1a73e8;
            --agent-bubble: #f1f5f9;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text);
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
        }
        #sidebar {
            width: 320px;
            background: var(--card-bg);
            border-right: 1px solid var(--border);
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        #main-chat {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        header {
            padding: 18px 24px;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            font-size: 1.2rem;
            margin: 0;
            color: var(--primary);
        }
        #chat-window {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .message {
            max-width: 75%;
            padding: 14px 18px;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 0.95rem;
            word-break: break-word;
        }
        .message.user {
            align-self: flex-end;
            background: var(--user-bubble);
            color: white;
            border-bottom-right-radius: 2px;
        }
        .message.agent {
            align-self: flex-start;
            background: var(--agent-bubble);
            color: var(--text);
            border-bottom-left-radius: 2px;
            border: 1px solid var(--border);
        }
        #input-container {
            padding: 18px 24px;
            background: var(--card-bg);
            border-top: 1px solid var(--border);
            display: flex;
            gap: 12px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
        }
        input[type="text"]:focus {
            border-color: var(--primary);
        }
        button {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: var(--primary-hover);
        }
        .quick-btn {
            background: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
            padding: 8px 12px;
            font-size: 0.82rem;
            text-align: left;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 6px;
            width: 100%;
        }
        .quick-btn:hover {
            background: #e2e8f0;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
            background: #e0f2fe;
            color: #0369a1;
        }
    </style>
</head>
<body>
    <div id="sidebar">
        <div>
            <h2>Employee Session</h2>
            <p><strong>Caller:</strong> Alex Tan (<span class="badge">EMP1024</span>)</p>
            <p><strong>Org:</strong> Altostrat Singapore (Tech)</p>
            <p><strong>Leave Balances:</strong></p>
            <ul>
                <li>Vacation: <strong>14.0 days</strong></li>
                <li>Sick Leave: <strong>12.0 days</strong></li>
            </ul>
        </div>
        <div>
            <h3>Quick Prompts (Test Scenarios)</h3>
            <button class="quick-btn" onclick="sendQuick('How many days of paid sick leave do I get in Singapore?')">📄 Sick Leave Policy</button>
            <button class="quick-btn" onclick="sendQuick('Can I expense a $45 gift card for my host?')">⚠️ Gift Card Gotcha ($45)</button>
            <button class="quick-btn" onclick="sendQuick('I need to take short-term medical leave next week. Can you set it up?')">🔄 UC-2.2 Cross-System Flow</button>
            <button class="quick-btn" onclick="sendQuick('What is the status of my laptop ticket INC-55100?')">🎫 ITSM Ticket Status</button>
            <button class="quick-btn" onclick="sendQuick('Can you write me a python script to reverse a string?')">🛡️ Out-of-Domain Block</button>
        </div>
        <div style="margin-top:auto; font-size:0.78rem; color:var(--text-muted);">
            Connected to <strong>philchen-project-elevate</strong><br>
            Powered by Vertex AI & ADK
        </div>
    </div>
    <div id="main-chat">
        <header>
            <h1>Altostrat Singapore HR Virtual Assistant</h1>
            <span class="badge">MVP 1 Active</span>
        </header>
        <div id="chat-window">
            <div class="message agent">
                Hello Alex! I am your Altostrat Singapore HR Assistant. How can I assist you today with policy inquiries, leave requests, or IT support tickets?
            </div>
        </div>
        <form id="input-container" onsubmit="handleSend(event)">
            <input type="text" id="user-input" placeholder="Ask about policy, leave balances, or submit a request..." autocomplete="off">
            <button type="submit">Send</button>
        </form>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');

        function appendMessage(sender, text) {
            const div = document.createElement('div');
            div.className = `message ${sender}`;
            div.innerHTML = text.replace(/\\n/g, '<br>');
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        async function handleSend(e) {
            if (e) e.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;

            appendMessage('user', text);
            userInput.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text, caller_id: 'EMP1024', session_id: 'web-session'})
                });
                const data = await response.json();
                appendMessage('agent', data.answer || 'No response returned.');
            } catch (err) {
                appendMessage('agent', 'Error connecting to agent service.');
            }
        }

        function sendQuick(prompt) {
            userInput.value = prompt;
            handleSend();
        }
    </script>
</body>
</html>"""
    return html_content


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
