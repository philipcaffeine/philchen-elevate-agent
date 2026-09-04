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
    list_incident_tickets,
    list_concepts,
)
from .guardrails import redact_spii

app = FastAPI(
    title="Altostrat Singapore HR Agentic Virtual Assistant",
    description="Enterprise HR Virtual Assistant for Policy Q&A, WorkWeek HCM, and ServiceImmediately ITSM.",
    version="1.1.0",
)


class ChatRequest(BaseModel):
    message: str
    caller_id: Optional[str] = "EMP1024"
    session_id: Optional[str] = "web-session-1"


@app.get("/healthz")
async def health_check():
    """Liveness probe for Cloud Run."""
    return {"status": "healthy", "service": "altostrat-hr-agent", "version": "1.1.0"}


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


@app.get("/api/tickets")
async def api_list_tickets(caller_id: Optional[str] = None):
    """Retrieve all incident tickets, optionally filtered by caller ID."""
    return list_incident_tickets(caller_id=caller_id)


@app.get("/api/tickets/user/{caller_id}")
async def api_user_tickets(caller_id: str):
    """Retrieve all incident tickets for a specific employee."""
    return list_incident_tickets(caller_id=caller_id)


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
            --recording-red: #ef4444;
        }
        * {
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text);
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        #sidebar {
            width: 360px;
            background: var(--card-bg);
            border-right: 1px solid var(--border);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 18px;
            overflow-y: auto;
        }
        #main-chat {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        header {
            padding: 16px 24px;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            font-size: 1.15rem;
            margin: 0;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 8px;
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
            max-width: 80%;
            padding: 14px 18px;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 0.95rem;
            word-break: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
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
            padding: 16px 24px;
            background: var(--card-bg);
            border-top: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .voice-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            font-size: 0.85rem;
            color: #b91c1c;
        }
        .voice-indicator.hidden {
            display: none;
        }
        .pulse-dot {
            width: 10px;
            height: 10px;
            background-color: var(--recording-red);
            border-radius: 50%;
            animation: pulse 1.2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        .voice-stop-btn {
            margin-left: auto;
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 0.75rem;
            cursor: pointer;
        }
        .input-row {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus {
            border-color: var(--primary);
        }
        .icon-btn {
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .icon-btn:hover {
            background: #e2e8f0;
            color: #1e293b;
        }
        .icon-btn.recording {
            background: #fee2e2;
            color: #dc2626;
            border-color: #f87171;
            animation: pulse 1.2s infinite;
        }
        button[type="submit"] {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 22px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
            height: 44px;
        }
        button[type="submit"]:hover {
            background: var(--primary-hover);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .section-header h3 {
            margin: 0;
            font-size: 0.92rem;
            font-weight: 600;
            color: #334155;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .btn-refresh {
            background: none;
            border: none;
            color: var(--primary);
            cursor: pointer;
            font-size: 1rem;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .btn-refresh:hover {
            background: #eff6ff;
        }
        .tickets-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 220px;
            overflow-y: auto;
        }
        .ticket-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            background: #f8fafc;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .ticket-card:hover {
            border-color: #93c5fd;
            background: #f0f7ff;
            transform: translateY(-1px);
        }
        .ticket-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .ticket-id {
            font-weight: 700;
            font-size: 0.85rem;
            color: #1e40af;
        }
        .ticket-desc {
            font-size: 0.82rem;
            color: #334155;
            margin-bottom: 6px;
            line-height: 1.3;
        }
        .ticket-footer {
            display: flex;
            justify-content: space-between;
            font-size: 0.72rem;
            color: var(--text-muted);
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
            transition: background 0.15s;
        }
        .quick-btn:hover {
            background: #e2e8f0;
        }
        .badge {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .badge-new { background: #e0f2fe; color: #0369a1; }
        .badge-progress { background: #fef3c7; color: #b45309; }
        .badge-hold { background: #ede9fe; color: #6d28d9; }
        .badge-resolved { background: #dcfce7; color: #15803d; }
        .badge-closed { background: #f1f5f9; color: #475569; }
        .badge-info { background: #e2e8f0; color: #334155; }
        .badge-mcp { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
        .user-meta-box {
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            font-size: 0.85rem;
        }
        .user-meta-box p {
            margin: 4px 0;
        }
        .user-meta-box ul {
            margin: 4px 0 0 16px;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="sidebar">
        <div>
            <div class="section-header">
                <h3>Employee Session</h3>
                <span class="badge badge-mcp" title="Connected via SaaS MCP Token">MCP Active</span>
            </div>
            <div class="user-meta-box">
                <p><strong>Caller:</strong> Alex Tan (<span class="badge badge-info">EMP1024</span>)</p>
                <p><strong>Org:</strong> Altostrat Singapore (Tech)</p>
                <p><strong>WorkWeek Balances:</strong></p>
                <ul>
                    <li>Vacation: <strong>14.0 days</strong></li>
                    <li>Sick Leave: <strong>12.0 days</strong></li>
                </ul>
            </div>
        </div>

        <div>
            <div class="section-header">
                <h3>Service Tickets (ITSM)</h3>
                <button class="btn-refresh" onclick="loadTickets()" title="Refresh tickets">↻</button>
            </div>
            <div id="tickets-list" class="tickets-list">
                <div style="font-size:0.8rem; color:var(--text-muted);">Loading tickets...</div>
            </div>
        </div>

        <div>
            <div class="section-header">
                <h3>Quick Scenarios</h3>
            </div>
            <button class="quick-btn" onclick="sendQuick('How many days of paid sick leave do I get in Singapore?')">📄 Sick Leave Policy</button>
            <button class="quick-btn" onclick="sendQuick('Can I expense a $45 gift card for my host?')">⚠️ Gift Card Gotcha ($45)</button>
            <button class="quick-btn" onclick="sendQuick('I need to take short-term medical leave next week. Can you set it up?')">🔄 UC-2.2 Cross-System Flow</button>
            <button class="quick-btn" onclick="sendQuick('What is the status of my laptop ticket INC-55100?')">🎫 ITSM Ticket Status</button>
            <button class="quick-btn" onclick="sendQuick('Can you write me a python script to reverse a string?')">🛡️ Out-of-Domain Block</button>
        </div>

        <div style="margin-top:auto; font-size:0.75rem; color:var(--text-muted); border-top: 1px solid var(--border); padding-top: 12px;">
            Connected: <strong>philchen-project-elevate</strong><br>
            Auth: <strong>admin@philchen.altostrat.com</strong><br>
            MCP Token: <code>mcp_Is3gTP...</code><br>
            Powered by Vertex AI & ADK
        </div>
    </div>

    <div id="main-chat">
        <header>
            <h1>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                </svg>
                Altostrat Singapore HR Virtual Assistant
            </h1>
            <div>
                <span class="badge badge-mcp">SaaS MCP Connected</span>
                <span class="badge badge-info">Voice Enabled</span>
            </div>
        </header>

        <div id="chat-window">
            <div class="message agent">
                Hello Alex! I am your Altostrat Singapore HR Assistant connected directly to WorkWeek HCM and ServiceImmediately ITSM. How can I assist you today with policy inquiries, leave bookings, or IT support tickets?
            </div>
        </div>

        <form id="input-container" onsubmit="handleSend(event)">
            <div id="voice-indicator" class="voice-indicator hidden">
                <span class="pulse-dot"></span>
                <span id="voice-status-text">Listening... Speak now</span>
                <button type="button" class="voice-stop-btn" onclick="stopVoice()">Stop</button>
            </div>
            <div class="input-row">
                <input type="text" id="user-input" placeholder="Ask about policy, leave balances, or submit a request..." autocomplete="off">
                <button type="button" id="voice-btn" class="icon-btn" title="Voice Input (Speech-to-Text)" onclick="toggleVoice()">
                    <svg id="mic-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                    </svg>
                </button>
                <button type="submit" id="send-btn">Send</button>
            </div>
        </form>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');
        const voiceBtn = document.getElementById('voice-btn');
        const voiceIndicator = document.getElementById('voice-indicator');
        const voiceStatusText = document.getElementById('voice-status-text');

        let recognition = null;
        let isRecording = false;

        function appendMessage(sender, text) {
            const div = document.createElement('div');
            div.className = `message ${sender}`;
            div.innerHTML = text.replace(/\\n/g, '<br>');
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        async function handleSend(e) {
            if (e) e.preventDefault();
            stopVoice();
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
                setTimeout(loadTickets, 600);
            } catch (err) {
                appendMessage('agent', 'Error connecting to agent service.');
            }
        }

        function sendQuick(prompt) {
            userInput.value = prompt;
            handleSend();
        }

        function getStatusBadge(label) {
            const l = (label || '').toLowerCase();
            if (l.includes('new')) return '<span class="badge badge-new">New</span>';
            if (l.includes('progress')) return '<span class="badge badge-progress">In Progress</span>';
            if (l.includes('hold')) return '<span class="badge badge-hold">On Hold</span>';
            if (l.includes('resolved')) return '<span class="badge badge-resolved">Resolved</span>';
            if (l.includes('closed')) return '<span class="badge badge-closed">Closed</span>';
            return `<span class="badge badge-info">${label || 'Active'}</span>`;
        }

        async function loadTickets() {
            const container = document.getElementById('tickets-list');
            try {
                const res = await fetch('/api/tickets');
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const tickets = await res.json();
                if (!tickets || tickets.length === 0) {
                    container.innerHTML = '<div style="font-size:0.8rem; color:var(--text-muted); padding:4px;">No active tickets.</div>';
                    return;
                }
                container.innerHTML = tickets.map(t => `
                    <div class="ticket-card" onclick="selectTicket('${t.ticket_id}')" title="Click to ask agent about ${t.ticket_id}">
                        <div class="ticket-top">
                            <span class="ticket-id">${t.ticket_id}</span>
                            ${getStatusBadge(t.state_label)}
                        </div>
                        <div class="ticket-desc">${t.short_description || 'No description provided'}</div>
                        <div class="ticket-footer">
                            <span>Pri: P${t.priority || 3}</span>
                            <span>${t.caller_id || 'EMP1024'}</span>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error('Failed to load tickets', err);
                container.innerHTML = `<div style="font-size:0.75rem; color:#b91c1c; padding:4px;">Failed to load tickets: ${err.message}</div>`;
            }
        }

        function selectTicket(ticketId) {
            userInput.value = `What is the current status and update on ticket ${ticketId}?`;
            handleSend();
        }

        function initVoice() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                console.warn('SpeechRecognition not supported in this browser.');
                if (voiceBtn) {
                    voiceBtn.title = 'Speech recognition not supported in this browser';
                    voiceBtn.style.opacity = '0.5';
                    voiceBtn.onclick = () => {
                        alert('Web Speech API is not supported in this browser. Please use Google Chrome.');
                    };
                }
                return;
            }

            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-SG';

            recognition.onstart = () => {
                isRecording = true;
                voiceBtn.classList.add('recording');
                voiceIndicator.classList.remove('hidden');
                voiceStatusText.textContent = 'Listening... Speak your prompt';
            };

            recognition.onresult = (event) => {
                let interim = '';
                let final = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }
                const speech = final || interim;
                if (speech) {
                    userInput.value = speech;
                }
            };

            recognition.onerror = (event) => {
                console.warn('Speech recognition notice:', event.error);
                if (event.error === 'not-allowed') {
                    alert('Microphone access was denied. Please allow microphone permissions in your browser settings.');
                }
                stopVoice();
            };

            recognition.onend = () => {
                stopVoice();
            };
        }

        function toggleVoice() {
            if (!recognition) {
                initVoice();
            }
            if (!recognition) return;

            if (isRecording) {
                recognition.stop();
                stopVoice();
            } else {
                try {
                    recognition.start();
                } catch (err) {
                    console.error('Speech recognition start failed:', err);
                    stopVoice();
                }
            }
        }

        function stopVoice() {
            isRecording = false;
            if (recognition) {
                try { recognition.stop(); } catch(e) {}
            }
            if (voiceBtn) voiceBtn.classList.remove('recording');
            if (voiceIndicator) voiceIndicator.classList.add('hidden');
        }

        window.addEventListener('DOMContentLoaded', () => {
            loadTickets();
            initVoice();
        });
    </script>
</body>
</html>"""
    return html_content


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
