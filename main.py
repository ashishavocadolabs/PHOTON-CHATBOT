from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from core.ai_orchestrator import handle_chat, reset_state
from services.auth_service import get_logged_user_name
from services.shipping_service import print_label
from pipelines.ingestion_pipeline import ingest_documents
from retrieval.vector_store import get_store_stats
from retrieval.rag_config import KNOWLEDGE_BASE_DIR
from fastapi.staticfiles import StaticFiles
import base64
import io
import os
import logging

logger = logging.getLogger("photon.main")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def home():
    name = get_logged_user_name() or "User"
    html_content = """
<!DOCTYPE html>
<html>
<head>
<title>Photon AI Assistant</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    box-sizing: border-box;
}

body {
    margin:0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size:15px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ===== FLOATING BUTTON ===== */
.chat-button {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1a3a4a, #2f6f6f);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 24px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
    overflow: visible;
    box-shadow: 0 4px 16px rgba(31, 78, 78, 0.35), 0 2px 6px rgba(0,0,0,0.1);
}

.chat-button svg {
    width: 22px;
    height: 22px;
    stroke: white;
}

/* ===== VOICE ACTIVE RING ===== */
.chat-button.voice-active::before,
.chat-button.voice-active::after {
    content: "";
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    z-index: -1;
}

.chat-button.voice-active::before {
    padding: 4px;
    background: conic-gradient(#00f2fe, #00c6ff, #00f2fe, #00ffcc, #00f2fe);
    animation: rotateRing 3s linear infinite;
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
}

.chat-button.voice-active::after {
    border: 2px solid #00f2fe;
    animation: rippleWave 2s infinite;
}

.chat-button.voice-active {
    animation: premiumPulse 1.6s infinite ease-in-out;
    box-shadow: 0 0 10px #00f2fe, 0 0 20px #00c6ff, 0 0 40px #00f2fe;
}

@keyframes rotateRing {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes rippleWave {
    0% { transform: scale(1); opacity: 0.8; }
    70% { transform: scale(1.6); opacity: 0; }
    100% { transform: scale(1.6); opacity: 0; }
}

@keyframes premiumPulse {
    0% { transform: scale(1); box-shadow: 0 0 5px #00f2fe, 0 0 15px #00f2fe; }
    50% { transform: scale(1.08); box-shadow: 0 0 20px #00f2fe, 0 0 40px #00f2fe, 0 0 80px rgba(0,242,254,0.8); }
    100% { transform: scale(1); box-shadow: 0 0 5px #00f2fe, 0 0 15px #00f2fe; }
}

.chat-button:hover {
    transform: translateY(-1px) scale(1.04);
    box-shadow: 0 6px 24px rgba(31, 78, 78, 0.45), 0 3px 10px rgba(0,0,0,0.15);
}

/* ===== CHAT BOX ===== */
.chat-box {
    position: fixed;
    bottom: 96px;
    right: 24px;
    width: 400px;
    height: 580px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow:
        0 20px 50px rgba(0,0,0,0.12),
        0 8px 24px rgba(0,0,0,0.08),
        0 0 0 1px rgba(0,0,0,0.04);
    display: none;
    flex-direction: column;
    overflow: hidden;
    opacity: 0;
    transform: translateY(16px) scale(0.96);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-box.active {
    opacity: 1;
    transform: translateY(0) scale(1);
}

/* ===== HEADER ===== */
.chat-header {
    height: 54px;
    background: linear-gradient(135deg, #1a3a4a 0%, #234e52 50%, #1f4648 100%);
    color: white;
    display: flex;
    align-items: center;
    padding: 0 12px;
    font-weight: 600;
    position: relative;
    overflow: visible;
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
    flex-shrink: 0;
    gap: 10px;
}

/* Subtle bottom highlight */
.chat-header::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
}

.header-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
}

.header-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: url('/static/photon-img.jpg') center/cover no-repeat;
    border: 1.5px solid rgba(255,255,255,0.25);
    flex-shrink: 0;
}

.header-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.header-title {
    font-size: 13.5px;
    font-weight: 600;
    letter-spacing: 0.2px;
    line-height: 1.2;
}

.header-status {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 400;
    color: rgba(255,255,255,0.7);
    line-height: 1.2;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4ade80;
    flex-shrink: 0;
    animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
}

/* ===== HEADER ICONS ===== */
.header-icon {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 6px;
}

.header-icon svg {
    width: 16px;
    height: 16px;
    stroke: rgba(255,255,255,0.85);
    stroke-width: 2;
    fill: none;
    transition: all 0.2s ease;
}

.header-icon:hover {
    background: rgba(255,255,255,0.1);
}

.header-icon:hover svg {
    stroke: #ffffff;
}

.header-icon.spin svg {
    animation: rotateRestart 0.6s linear;
}

@keyframes rotateRestart {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* ===== MESSAGES AREA ===== */
.chat-messages {
    flex: 1;
    padding: 20px 16px;
    overflow-y: auto;
    background: #f8f9fb;
    color: #000000;
    position: relative;
    z-index: 1;
    scroll-behavior: smooth;
}

.chat-messages::-webkit-scrollbar {
    width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
    background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
    background: rgba(47, 111, 111, 0.2);
    border-radius: 10px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: rgba(47, 111, 111, 0.4);
}

.chat-messages::before {
    content: "";
    position: fixed;
    inset: 0;
    background: url('/static/photon-img.jpg') center center no-repeat;
    background-size: 280px;
    opacity: 0.04;
    pointer-events: none;
    z-index: 0;
}

/* ===== BOT ROW ===== */
.bot-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 14px;
    animation: fadeIn 0.3s ease;
}

.bot-avatar {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: url('/static/photon-img.jpg') center/cover no-repeat;
    border: 1.5px solid #2f6f6f;
    flex-shrink: 0;
    margin-top: 2px;
    box-shadow: 0 1px 4px rgba(47, 111, 111, 0.15);
}

.bot-avatar.thinking {
    animation: aiPulse 1.4s ease-in-out infinite;
}

@keyframes aiPulse {
    0% { transform: scale(1); box-shadow: 0 0 0 rgba(47,111,111,0); }
    50% { transform: scale(1.08); box-shadow: 0 0 12px rgba(47,111,111,0.4); }
    100% { transform: scale(1); box-shadow: 0 0 0 rgba(47,111,111,0); }
}

.bot-content {
    display: flex;
    flex-direction: column;
    max-width: calc(100% - 40px);
}

/* ===== BOT MESSAGE ===== */
.bot {
    background: #ffffff;
    color: #1e2d2d;
    padding: 14px 18px;
    border-radius: 4px 16px 16px 16px;
    margin-bottom: 8px;
    font-size: 13.5px;
    line-height: 1.6;
    max-width: 100%;
    border: 1px solid #eaedee;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    position: relative;
    z-index: 5;
    word-wrap: break-word;
    letter-spacing: 0.1px;
}

/* ===== USER MESSAGE ===== */
.user {
    background: linear-gradient(135deg, #2f6f6f, #1f5050);
    color: white;
    padding: 11px 16px;
    border-radius: 16px 16px 4px 16px;
    margin-left: auto;
    margin-bottom: 12px;
    font-size: 13.5px;
    line-height: 1.5;
    max-width: 75%;
    width: fit-content;
    word-wrap: break-word;
    box-shadow: 0 2px 8px rgba(31, 78, 78, 0.15);
    position: relative;
    z-index: 5;
    animation: fadeIn 0.25s ease;
    letter-spacing: 0.1px;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ===== TYPING INDICATOR ===== */
.typing span {
    height: 6px;
    width: 6px;
    background: #2f6f6f;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
    animation: bounce 1.4s infinite;
}

.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
    0%,80%,100% { transform: scale(0); }
    40% { transform: scale(1); }
}

/* ===== SENDING BUBBLE ===== */
.sending {
    background: linear-gradient(135deg, #2f6f6f, #1a4a4a);
    color: white;
    padding: 8px 16px;
    border-radius: 18px 18px 4px 18px;
    margin-left: auto;
    margin-bottom: 12px;
    font-size: 13px;
    width: fit-content;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.12);
    animation: fadeIn 0.2s ease;
}

.sending span {
    width: 5px;
    height: 5px;
    background: rgba(255,255,255,0.8);
    border-radius: 50%;
    display: inline-block;
    animation: sendBounce 1.2s infinite;
}

.sending span:nth-child(2) { animation-delay: 0.2s; }
.sending span:nth-child(3) { animation-delay: 0.4s; }

@keyframes sendBounce {
    0%,80%,100% { transform: scale(0); }
    40% { transform: scale(1); }
}

/* ===== INPUT AREA ===== */
.chat-input {
    display: flex;
    padding: 10px 12px;
    background: #ffffff;
    gap: 8px;
    position: relative;
    border-radius: 0 0 16px 16px;
    border-top: 1px solid #eef0f2;
    align-items: center;
    flex-shrink: 0;
}

.chat-input::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    height: 2px;
    width: 100%;
    background: linear-gradient(90deg, transparent, rgba(47, 111, 111, 0.3), transparent);
    animation: subtleSlide 3s linear infinite;
    opacity: 0.6;
}

@keyframes subtleSlide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.chat-input input {
    flex: 1;
    padding: 9px 16px;
    border-radius: 22px;
    border: 1px solid #dde2e6;
    outline: none;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    background: #f5f7f8;
    transition: all 0.2s ease;
    color: #1a2b2b;
    min-width: 0;
}

.chat-input input:focus {
    border-color: #2f6f6f;
    background: #ffffff;
    box-shadow: 0 0 0 2px rgba(47, 111, 111, 0.06);
}

.chat-input input::placeholder {
    color: #a0aab3;
    font-size: 13px;
}

/* Shared button base */
.chat-input button {
    width: 36px;
    height: 36px;
    min-width: 36px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    flex-shrink: 0;
    padding: 0;
    position: relative;
    overflow: hidden;
}

.chat-input button svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
}

/* Mic button — outlined circle */
.chat-input .mic-btn {
    background: #f0f3f5;
    border: 1.5px solid #d0d7dc;
}

.chat-input .mic-btn svg {
    stroke: #5a6a7a;
    stroke-width: 2;
}

.chat-input .mic-btn:hover {
    background: #e6eef0;
    border-color: #2f6f6f;
}

.chat-input .mic-btn:hover svg {
    stroke: #2f6f6f;
}

.chat-input .mic-btn.voice-on {
    background: #2f6f6f;
    border-color: #2f6f6f;
}

.chat-input .mic-btn.voice-on svg {
    stroke: white;
}

/* Send button — solid teal */
.chat-input .send-btn {
    background: #2f6f6f;
}

.chat-input .send-btn svg {
    stroke: white;
    width: 15px;
    height: 15px;
}

.chat-input .send-btn:hover {
    background: #245858;
    transform: scale(1.05);
}

/* ===== OPTION BUTTONS ===== */
.options-wrapper {
    display: flex;
    flex-wrap: wrap;
    margin-top: 6px;
    gap: 6px;
    padding: 2px;
}

.option-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: calc(50% - 4px);
    padding: 16px 10px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
    font-size: 12.5px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    color: #1a3a4a;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
    text-align: center;
    word-break: break-word;
    white-space: normal;
    line-height: 1.4;
    position: relative;
    z-index: 10;
    gap: 8px;
    letter-spacing: 0.2px;
}

.option-btn svg {
    width: 20px;
    height: 20px;
    stroke: #2f6f6f;
    stroke-width: 1.75;
    transition: all 0.2s ease;
}

.option-btn:hover {
    transform: translateY(-1px);
    border-color: #2f6f6f;
    background: #f0f7f7;
    box-shadow: 0 4px 16px rgba(31, 78, 78, 0.12);
}

.option-btn:hover svg {
    stroke: #1a4a4a;
}

.option-btn:active {
    transform: scale(0.98);
    background: linear-gradient(135deg, #1a3a4a, #2f6f6f);
    color: white;
    border-color: transparent;
}

.option-btn:active svg {
    stroke: white;
}

/* ===== TOOLTIPS ===== */
.tooltip {
    position: relative;
}

.tooltip-text {
    position: absolute;
    bottom: 130%;
    left: 50%;
    transform: translateX(-50%) translateY(5px);
    background: #1a3a4a;
    color: #fff;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 500;
    border-radius: 6px;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 2;
}

.tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border-width: 5px;
    border-style: solid;
    border-color: #1a3a4a transparent transparent transparent;
}

.tooltip:hover .tooltip-text {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

.tooltip-bottom .tooltip-text {
    top: 46px;
    bottom: auto;
    transform: translateX(-50%);
}

.tooltip-bottom .tooltip-text::after {
    top: -10px;
    bottom: auto;
    border-color: transparent transparent #1a3a4a transparent;
}

/* ===== BOT TYPING ROW ===== */
.bot-typing-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    margin-bottom: 14px;
}

.bot-typing {
    background: #ffffff;
    padding: 10px 16px;
    border-radius: 18px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border: 1px solid #e8ecef;
}

/* ===== HI BUBBLE ===== */
.chat-hi-bubble {
    position: fixed;
    bottom: 90px;
    right: 24px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: #ffffff;
    color: #1a2b2b;
    padding: 10px 16px;
    border-radius: 14px;
    font-size: 13px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.04);
    opacity: 0;
    transform: translateY(16px) scale(0.92);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: none;
}

.chat-hi-avatar {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: url('/static/photon-img.jpg') center/cover no-repeat;
    border: 1.5px solid #2f6f6f;
    flex-shrink: 0;
}

.chat-hi-bubble::after {
    content: "";
    position: absolute;
    bottom: -6px;
    right: 22px;
    border-width: 6px;
    border-style: solid;
    border-color: #ffffff transparent transparent transparent;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.05));
}

/* ===== FLOATING ANIMATIONS ===== */
.floating-hi {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 55px;
    height: 120px;
    pointer-events: none;
}

.hi-popup {
    position: absolute;
    bottom: 8px;
    left: -20px;
    background: #2f6f6f;
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    opacity: 0;
    transform: translateY(15px);
    transition: all 0.4s ease;
    z-index: 1;
    white-space: nowrap;
}

/* ===== GLOBAL SVG DEFAULT ===== */
svg {
    width: 16px;
    height: 16px;
    stroke: currentColor;
    stroke-width: 2;
    fill: none;
    flex-shrink: 0;
}

/* ===== SERVICE CARD ===== */
.service-card {
    width: 100%;
    text-align: left;
    padding: 2px 0;
}

.service-title {
    font-weight: 600;
    font-size: 12.5px;
    margin-bottom: 8px;
    word-break: break-word;
    color: #1a3a4a;
    letter-spacing: 0.2px;
}

.service-row {
    display: flex;
    justify-content: space-between;
    font-size: 11.5px;
    color: #4a6060;
    gap: 8px;
}

.service-row span {
    display: flex;
    align-items: center;
    gap: 4px;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 480px) {
    .chat-box {
        width: calc(100vw - 16px);
        height: calc(100vh - 120px);
        right: 8px;
        bottom: 80px;
        border-radius: 16px;
    }
}
</style>
</head>

<body>
<div class="chat-hi-bubble" id="chatHi">

    <div class="chat-hi-avatar"></div>

    <div>
        <b>Photon AI</b><br>
        <span style="font-size:12px;color:#5a6a6a">How can I assist you?</span>
    </div>

</div>

<div class="chat-button" id="chatBtn" onclick="toggleChat()">

<svg viewBox="0 0 24 24" fill="none">
<path d="M21 15a4 4 0 0 1-4 4H7l-4 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"
stroke="currentColor" stroke-width="2"/>
</svg>

</div>

<div class="chat-box" id="chatBox">

    <div class="chat-header">

        <!-- BRAND AREA -->
        <div class="header-brand">
            <div class="header-avatar"></div>
            <div class="header-info">
                <div class="header-title">Photon AI</div>
                <div class="header-status">
                    <span class="status-dot"></span>
                    Online
                </div>
            </div>
        </div>

        <!-- ACTION ICONS -->
        <div class="header-actions">
            <div class="header-icon tooltip tooltip-bottom" onclick="resetChat(this)">
                <svg viewBox="0 0 24 24">
                    <path d="M21 12a9 9 0 1 1-3-6.7"/>
                    <polyline points="21 3 21 9 15 9"/>
                </svg>
                <span class="tooltip-text">Restart</span>
            </div>
            <div class="header-icon tooltip tooltip-bottom" onclick="closeChat()">
                <svg viewBox="0 0 24 24">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
                <span class="tooltip-text">Close</span>
            </div>
        </div>

    </div>

    <div class="chat-messages" id="messages">

        <div class="bot-row">

            <div class="bot-avatar"></div>

            <div class="bot-content">

                <div class="bot">
                    Welcome, <b>{name}</b>. I'm your <b>Photon AI Assistant</b> for logistics operations.
                    <br><br>How can I help you today?
                </div>

                <div class="options-wrapper">

                    <button class="option-btn" onclick="sendOption('create shipment','Create Shipment')">

                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M3 7l9-4 9 4-9 4-9-4z" stroke="currentColor" stroke-width="2"/>
                    <path d="M3 7v10l9 4 9-4V7" stroke="currentColor" stroke-width="2"/>
                    </svg>

                    Create Shipment
                    </button>

                    <button class="option-btn" onclick="sendOption('quote','Get Quote')">

                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                    <path d="M8 12h8M12 8v8" stroke="currentColor" stroke-width="2"/>
                    </svg>

                    Get Quote
                    </button>

                    <button class="option-btn" onclick="sendOption('tracking','Track Shipment')">

                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="1" y="3" width="15" height="13" stroke="currentColor" stroke-width="2"/>
                    <polygon points="16,8 20,8 23,11 23,16 16,16" stroke="currentColor" stroke-width="2"/>
                    <circle cx="5.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
                    <circle cx="18.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
                    </svg>

                    Track Shipment
                    </button>

                    <button class="option-btn" onclick="sendOption('print label','Print Label')">

                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="6" y="9" width="12" height="8" stroke="currentColor" stroke-width="2"/>
                    <path d="M6 9V5h12v4" stroke="currentColor" stroke-width="2"/>
                    <path d="M9 17h6" stroke="currentColor" stroke-width="2"/>
                    </svg>

                    Print Label
                    </button>

                </div>

            </div>

        </div>
    </div>

    <div class="chat-input">
    <button class="mic-btn" onclick="toggleVoice()" title="Mic">
    <svg viewBox="0 0 24 24">
    <rect x="9" y="2" width="6" height="12" rx="3"></rect>
    <path d="M5 10v2a7 7 0 0 0 14 0v-2"></path>
    <line x1="12" y1="19" x2="12" y2="22"></line>
    </svg>
    </button>
        <input type="text" id="messageInput"
        placeholder="Type a message..."
        onkeydown="if(event.key==='Enter'){sendMessage();}">
        <button class="send-btn" onclick="sendMessage()" title="Send">
        <svg viewBox="0 0 24 24">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>
        </button>
    </div>

</div>

<script>

const USER_NAME = "{name}";
let hiInterval = null;

/* Toggle Chat */
function toggleChat() {

    let box = document.getElementById("chatBox");
    let bubble = document.getElementById("chatHi");

    if (box.classList.contains("active")) {

        // CLOSE CHAT
        box.classList.remove("active");
        setTimeout(()=>{ box.style.display="none"; },300);

        // Show Hi bubble again
        startHiBubble();

    } else {

        // OPEN CHAT
        box.style.display="flex";
        setTimeout(()=>{ box.classList.add("active"); },10);

        // Hide Hi bubble
        if (bubble) {
            bubble.style.display = "none";
        }

        // Stop animation while open
        if (hiInterval) {
            clearInterval(hiInterval);
        }
    }
}

let headerLoop = null;
/* Header is now static enterprise branding — no animation needed */

/* Typing Indicator */
function showTyping(){

    let messagesDiv = document.getElementById("messages");

    let row = document.createElement("div");
    row.className = "bot-typing-row";
    row.id = "typing";

    let avatar = document.createElement("div");
    avatar.className = "bot-avatar thinking";

    let typing = document.createElement("div");
    typing.className = "bot-typing";

    typing.innerHTML = `
        <div class="typing">
            <span></span><span></span><span></span>
        </div>
    `;

    row.appendChild(avatar);
    row.appendChild(typing);

    messagesDiv.appendChild(row);

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/* Send Message */
async function sendMessage() {
    let input = document.getElementById("messageInput");
    let message = input.value.trim();
    if (!message) return;

    let messagesDiv = document.getElementById("messages");

    // Show user message
    let userDiv = document.createElement("div");
    userDiv.className = "user";
    userDiv.innerText = message;
    messagesDiv.appendChild(userDiv);
    input.value = "";

    // Show sending bubble
    let sendingDiv = document.createElement("div");
    sendingDiv.className = "sending";
    sendingDiv.id = "sendingBubble";
    sendingDiv.innerHTML = `
        Sending
        <span></span><span></span><span></span>
    `;
    messagesDiv.appendChild(sendingDiv);

    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    });

    let data = await response.json();

    // Remove sending bubble
    let bubble = document.getElementById("sendingBubble");
    if (bubble) bubble.remove();

    // Now show bot typing
    showTyping();
    setTimeout(() => {
        removeTyping();
        renderBotResponse(data);
    }, 500);
}

/* Render Bot */
function renderBotResponse(data) {

    let messagesDiv = document.getElementById("messages");

    // Create row container
    let row = document.createElement("div");
    row.className = "bot-row";

    // Avatar
    let avatar = document.createElement("div");
    avatar.className = "bot-avatar";

    let content = document.createElement("div");
    content.className = "bot-content";

    // Message bubble
    let botDiv = document.createElement("div");
    botDiv.className = "bot";
    botDiv.innerHTML = data.response || "Something went wrong.";

    content.appendChild(botDiv);

    // Append
    /* OPTIONS */
    if (data.options && data.options.length > 0) {

        let wrapper = document.createElement("div");
        wrapper.className = "options-wrapper";

        data.options.forEach(option => {

            let btn = document.createElement("button");
            btn.className = "option-btn";
            btn.innerHTML = option.label;

            btn.onclick = function () {
    
                wrapper.remove();
                sendOption(option.value, option.label);
            };

            wrapper.appendChild(btn);
        });

        content.appendChild(wrapper);
    }

    row.appendChild(avatar);
    row.appendChild(content);

    messagesDiv.appendChild(row);

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendOption(value, label) {
    let messagesDiv = document.getElementById("messages");

    // Strip HTML from label for clean user bubble display
    let tempDiv = document.createElement("div");
    tempDiv.innerHTML = label;
    let cleanLabel = tempDiv.textContent.trim().replace(/\s+/g, ' ');

    messagesDiv.innerHTML += `<div class="user">${cleanLabel}</div>`;
    showTyping();

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: value })
    });

    let data = await response.json();
    removeTyping();
    renderBotResponse(data);
}

function removeTyping(){

    let typing = document.getElementById("typing");

    if(typing){

        let avatar = typing.querySelector(".bot-avatar");

        if(avatar){
            avatar.classList.remove("thinking");
        }

        typing.remove();
    }
}

/* ================= VOICE SYSTEM ================= */

let recognition;
let listening=false;
let wakeWord="hey photon";

function toggleVoice(){

    let chatLogo = document.getElementById("chatBtn");
    let micBtn = document.querySelector(".mic-btn");

    if(listening){

        recognition.stop();
        listening=false;

        chatLogo.classList.remove("voice-active");
        if(micBtn) micBtn.classList.remove("voice-on");

    }else{

        startVoice();

        chatLogo.classList.add("voice-active");
        if(micBtn) micBtn.classList.add("voice-on");
    }
}

function startVoice(){
    if(!('webkitSpeechRecognition' in window)){
        alert("Speech not supported in this browser");
        return;
    }

    recognition=new webkitSpeechRecognition();
    recognition.lang="en-US";
    recognition.continuous=true;
    recognition.interimResults=false;
    if(listening){
        recognition.start();
    }

    listening=true;
    document.getElementById("chatBtn").classList.add("listening");

    recognition.onresult = function(event){
        let transcript = event.results[event.results.length-1][0].transcript.toLowerCase().trim();

        // Ignore very short words to prevent loop
        if(transcript.length < 3){
            return;
        }

        if(transcript.includes(wakeWord)){
            speakText("Yes " + USER_NAME + ", I am listening.");
            return;
        }

        document.getElementById("messageInput").value = transcript;
        sendMessage();
    };
}

/* Text To Speech */
function speakText(text){
    if(!text) return;

    // Stop mic before speaking
    if(recognition && listening){
        recognition.stop();
    }

    window.speechSynthesis.cancel();

    let speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-US";
    speech.rate = 1;

    speech.onend = function(){
        // Restart mic only if voice mode enabled
        if(listening){
            recognition.start();
        }
    };

    window.speechSynthesis.speak(speech);
}

function closeChat(){
    let box = document.getElementById("chatBox");
    box.classList.remove("active");
    setTimeout(()=>{ box.style.display="none"; },300);
}

let resetInProgress = false;

async function resetChat(element){

    if(resetInProgress) return;   // prevent multiple calls
    resetInProgress = true;

    // rotate animation
    if(element){
        element.classList.add("spin");
        setTimeout(()=>{
            element.classList.remove("spin");
        },600);
    }

    // stop voice
    if(recognition && listening){
        recognition.stop();
        listening = false;
        document.getElementById("chatBtn").classList.remove("voice-active");
    }

    // clear UI
    let messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML = `
    <div class="bot-row">

        <div class="bot-avatar"></div>

        <div class="bot-content">

            <div class="bot">
                Welcome, <b>${USER_NAME}</b>. I'm your <b>Photon AI Assistant</b> for logistics operations.
                <br><br>How can I help you today?
            </div>

            <div class="options-wrapper">

                <button class="option-btn" onclick="sendOption('create shipment','Create Shipment')">

                <svg viewBox="0 0 24 24">
                <path d="M3 7l9-4 9 4-9 4-9-4z"/>
                <path d="M3 7v10l9 4 9-4V7"/>
                </svg>

                Create Shipment
                </button>

                <button class="option-btn" onclick="sendOption('quote','Get Quote')">

                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M8 12h8M12 8v8" stroke="currentColor" stroke-width="2"/>
                </svg>

                Get Quote
                </button>

                <button class="option-btn" onclick="sendOption('tracking','Track Shipment')">

                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect x="1" y="3" width="15" height="13" stroke="currentColor" stroke-width="2"/>
                <polygon points="16,8 20,8 23,11 23,16 16,16" stroke="currentColor" stroke-width="2"/>
                <circle cx="5.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
                <circle cx="18.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
                </svg>

                Track Shipment
                </button>

                <button class="option-btn" onclick="sendOption('print label','Print Label')">

                <svg viewBox="0 0 24 24">
                <rect x="6" y="9" width="12" height="8"/>
                <path d="M6 9V5h12v4"/>
                <path d="M9 17h6"/>
                </svg>

                Print Label
                </button>

            </div>

        </div>

    </div>
    `;

    // backend reset
    await fetch("/reset", { method: "POST" });

    setTimeout(()=>{ resetInProgress = false; }, 800);
}

function startHiBubble(){

    const bubble = document.getElementById("chatHi");

    function animate(){

        bubble.style.display="flex";

        setTimeout(()=>{
            bubble.style.opacity=1;
            bubble.style.transform="translateY(0) scale(1)";
        },50);

        setTimeout(()=>{
            bubble.style.opacity=0;
            bubble.style.transform="translateY(15px) scale(0.9)";
        },4500);
    }

    animate();

    hiInterval = setInterval(animate,8000);
}

startHiBubble();
</script>

</body>
</html>
"""
    return html_content.replace("{name}", name)

@app.post("/chat")
async def chat(request: ChatRequest):
    return handle_chat(request.message)

@app.post("/reset")
async def reset_chat():
    reset_state()
    return {"status": "reset done"}

@app.get("/favicon.ico")
async def favicon():
    return {}
# ================= DOWNLOAD LABEL =================

@app.get("/download-label")
def download_label(tracking_no: str):

    result = print_label(tracking_no)

    # API error handling
    if not result or result.get("statusCode") != 200:
        return {"error": result.get("message", "Label not available")}

    data = result.get("data")

    if not data:
        return {"error": "No label data returned"}

    # case 1: data is dict
    if isinstance(data, dict):
        pdf_base64 = data.get("fileData")

    # case 2: data is raw base64 string
    elif isinstance(data, str):
        pdf_base64 = data

    else:
        return {"error": "Invalid label format"}

    if not pdf_base64:
        return {"error": "Label file not found"}

    pdf_bytes = base64.b64decode(pdf_base64)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=label_{tracking_no}.pdf"
        }
    )


# =====================================================
# RAG - KNOWLEDGE BASE ENDPOINTS
# =====================================================

@app.on_event("startup")
async def startup_ingest():
    """Auto-ingest documents from knowledge_base/ on server start."""
    try:
        result = ingest_documents()
        logger.info(f"Startup ingestion: {result['message']}")
    except Exception as e:
        logger.error(f"Startup ingestion failed: {e}")


@app.post("/rag/ingest")
async def rag_ingest(force: bool = False):
    """Trigger document ingestion. Use force=true to re-ingest all."""
    try:
        result = ingest_documents(force=force)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/rag/upload")
async def rag_upload(file: UploadFile = File(...)):
    """Upload a .txt file to knowledge_base/ and auto-ingest."""
    if not file.filename.endswith(".txt"):
        return {"status": "error", "message": "Only .txt files are supported."}

    safe_name = os.path.basename(file.filename)
    dest = os.path.join(KNOWLEDGE_BASE_DIR, safe_name)

    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    result = ingest_documents()
    return {
        "status": "uploaded",
        "file": safe_name,
        "ingestion": result,
    }


@app.get("/rag/stats")
async def rag_stats():
    """Return vector store statistics."""
    try:
        stats = get_store_stats()
        files = []
        for fname in os.listdir(KNOWLEDGE_BASE_DIR):
            if fname.endswith(".txt"):
                files.append(fname)
        stats["knowledge_base_files"] = files
        return stats
    except Exception as e:
        return {"status": "error", "message": str(e)}