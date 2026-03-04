from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.ai_orchestrator import handle_chat, reset_state
from services.auth_service import get_logged_user_name
from fastapi.staticfiles import StaticFiles

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
body {
    margin:0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size:15px;
}

/* Floating Button */
.chat-button {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: #2f6f6f;
    color: #00f2fe;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 24px;
    transition: 0.3s ease;
    z-index: 1000;
    overflow: visible;
}

/* ===== AI ENERGY RING SYSTEM ===== */

.chat-button.voice-active::before,
.chat-button.voice-active::after {
    content: "";
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    z-index: -1;
}

/*  Rotating Neon Border */
.chat-button.voice-active::before {
    padding: 4px;
    background: conic-gradient(
        #00f2fe,
        #00c6ff,
        #00f2fe,
        #00ffcc,
        #00f2fe
    );
    animation: rotateRing 3s linear infinite;
    mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
    -webkit-mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
            mask-composite: exclude;
}

/*  Outer Ripple Wave */
.chat-button.voice-active::after {
    border: 2px solid #00f2fe;
    animation: rippleWave 2s infinite;
}

/*  Neon Glow Core */
.chat-button.voice-active {
    animation: pulseCore 1.8s infinite ease-in-out;
    box-shadow:
        0 0 10px #00f2fe,
        0 0 25px #00f2fe,
        0 0 50px #00c6ff,
        0 0 80px rgba(0,242,254,0.6);
}

/* ===== Animations ===== */

@keyframes rotateRing {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes rippleWave {
    0% {
        transform: scale(1);
        opacity: 0.8;
    }
    70% {
        transform: scale(1.6);
        opacity: 0;
    }
    100% {
        transform: scale(1.6);
        opacity: 0;
    }
}

@keyframes pulseCore {
    0% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.08);
    }
    100% {
        transform: scale(1);
    }
}
.chat-button:hover {
    transform: scale(1.05);
}


/* Chat Box */
.chat-box {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 380px;
    height: 520px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    display: none;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #e0e0e0;
    opacity:0;
    transform:translateY(20px);
    transition: all 0.3s ease;
}
.chat-box.active {
    opacity:1;
    transform:translateY(0);
}

.chat-header {
    overflow: visible;
    position: relative;
}
/* Header */
.chat-header {
    height: 50px;
    background: #2f6f6f;
    color: white;
    display:flex;
    align-items:center;
    justify-content: space-between;
    padding: 0 15px;
    font-weight: 600;
}

.chat-messages {
    flex:1;
    padding:15px;
    overflow-y:auto;
    background:#f2f3f7;
    color:#000000;
    position:relative;
    z-index:1;
}

.chat-messages::before {
    content:"";
    position:fixed;   /* FIX */
    inset:0;
    background: url('/static/photon-img.jpg') center center no-repeat;
    background-size: 280px;
    opacity: 0.05;       /* softer */
    pointer-events:none;
    z-index:0;
}
/* ===== LOGO ANIMATION AREA ===== */
.logo-area {
    display:flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    flex:1;
}
.box-icon, .truck-icon {
    position:relative;
    top:0;
    left:0;
    right:0;
    font-size:20px;
    opacity:1;
}

.hi-text {
    position:relative;
    font-size:14px;
    font-weight:600;
    opacity:1;
}
/* ===== PREMIUM HEADER ICON ===== */

.header-icon {
    width: 26px;
    height: 26px;
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    transition: transform 0.2s ease;
}

/* icon size */
.header-icon svg {
    width:18px;
    height:18px;
    stroke:white;
    stroke-width:2;
    fill:none;
}

/* hover */
.header-icon:hover {
    transform: scale(1.1);
}

.header-icon:hover svg {
    stroke: #00f2fe;
}
/* Animations */
@keyframes jumpBox {
    0% { transform: translateY(20px); opacity:0; }
    50% { transform: translateY(-12px); opacity:1; }
    100% { transform: translateY(0); opacity:1; }
}

@keyframes slideIn {
    from { transform: translateX(-40px); opacity:0; }
    to { transform: translateX(0); opacity:1; }
}
@keyframes smoothErase {
    0% {
        opacity: 1;
        transform: translateY(0);
    }
    40% {
        opacity: 1;
    }
    70% {
        opacity: 0.5;
    }
    100% {
        opacity: 0;
        transform: translateY(-8px);
    }
}

/* Bot Row Layout */
.bot-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 14px;
}

/* Avatar */
.bot-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: url('/static/photon-img.jpg') center/cover no-repeat;
    border: 2px solid #2f6f6f;
    flex-shrink: 0;
    margin-top: 2px;
}

/* AI thinking avatar animation */
.bot-avatar.thinking{
    animation: aiPulse 1.4s ease-in-out infinite;
}

@keyframes aiPulse{
    0%{
        transform:scale(1);
        box-shadow:0 0 0 rgba(47,111,111,0);
    }
    50%{
        transform:scale(1.08);
        box-shadow:0 0 12px rgba(47,111,111,0.5);
    }
    100%{
        transform:scale(1);
        box-shadow:0 0 0 rgba(47,111,111,0);
    }
}

.bot-content {
    display: flex;
    flex-direction: column;
}

/* Bot Message */
.bot {
    background: #f4f6f8;
    color: #1f2d2d;

    padding: 12px 16px;

    border-radius: 18px 18px 18px 4px;

    margin-bottom: 12px;

    font-size: 14px;

    max-width: 75%;

    box-shadow: 0 4px 10px rgba(0,0,0,0.06);

    position: relative;

    animation: fadeIn 0.25s ease;
}

.bot::before{
    content:"";
    position:absolute;
    left:-6px;
    top:14px;

    width:0;
    height:0;

    border-top:6px solid transparent;
    border-bottom:6px solid transparent;
    border-right:6px solid #eef1f4;
}

/* User Message */
.user {
    background:#2f6f6f;
    color:white;

    padding:10px 14px;
    border-radius:18px 18px 4px 18px;

    margin-left:auto;
    margin-bottom:12px;

    font-size:14px;

    max-width:65%;
    width:fit-content;

    word-wrap:break-word;

    box-shadow:0 3px 8px rgba(0,0,0,0.15);

    animation:fadeIn 0.25s ease;
}

@keyframes fadeIn {
    from{opacity:0; transform:translateY(10px);}
    to{opacity:1; transform:translateY(0);}
}


/* Typing */
.typing span {
    height:6px;
    width:6px;
    background:#555;
    border-radius:50%;
    display:inline-block;
    margin:0 2px;
    animation:bounce 1.4s infinite;
}
.typing span:nth-child(2){animation-delay:0.2s;}
.typing span:nth-child(3){animation-delay:0.4s;}


@keyframes bounce {
    0%,80%,100% { transform:scale(0);}
    40% { transform:scale(1);}
}

/* Sending Bubble */

.sending {
    background:#2f6f6f;
    color:white;

    padding:8px 12px;

    border-radius:18px 18px 4px 18px;

    margin-left:auto;
    margin-bottom:12px;

    font-size:13px;

    width:fit-content;

    display:flex;
    align-items:center;
    gap:6px;

    box-shadow:0 3px 8px rgba(0,0,0,0.15);

    animation:fadeIn 0.2s ease;
}
/* Animated dots */
.sending span {
    width:6px;
    height:6px;
    background:white;
    border-radius:50%;
    display:inline-block;
    animation: sendBounce 1.2s infinite;
}

.sending span:nth-child(2){animation-delay:0.2s;}
.sending span:nth-child(3){animation-delay:0.4s;}

@keyframes sendBounce {
    0%,80%,100% { transform:scale(0); }
    40% { transform:scale(1); }
}
/* Input Area */
.chat-input {
    display:flex;
    padding:10px;
    background:#ffffff;
    border-top:1px solid #e0e0e0;
    gap:10px;
    position: relative;
    border-radius: 0 0 16px 16px;
}
/* ===== PREMIUM SUBTLE BOTTOM BORDER ===== */

.chat-input {
    position: relative;
    border-top: 1px solid #e0e0e0;
}

/* Thin animated line */
.chat-input::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    height: 2px;
    width: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        #00c6ff,
        transparent
    );
    animation: subtleSlide 3s linear infinite;
    opacity: 0.4;
}

@keyframes subtleSlide {
    0% {
        transform: translateX(-100%);
    }
    100% {
        transform: translateX(100%);
    }
}

.chat-input input {
    flex:1;
    padding:10px 12px;
    border-radius:20px;
    border:1px solid #ccc;
    outline:none;
    font-size:14px;
}

.chat-input button {
    margin-left:8px;
    width:40px;
    height:40px;
    border-radius:50%;
    border:none;
    background:#2f6f6f;
    color:white;
    cursor:pointer;
    font-size:14px;
}

/* Options */
/* === Compact Popup Option Cards === */

.option-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;

    width: 48%;                /* 2 per row */
    margin: 6px 1%;
    padding: 10px 12px;

    border-radius: 14px;
    border: 1px solid rgba(47,111,111,0.4);

    background: linear-gradient(
        135deg,
        rgba(47,111,111,0.15),
        rgba(47,111,111,0.05)
    );

    color: #1f4e4e;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;

    transition: all 0.25s ease;
    backdrop-filter: blur(6px);

    box-shadow: 0 6px 14px rgba(0,0,0,0.08);
}

/* Hover */
.option-btn:hover {
    transform: translateY(-3px);
    background: linear-gradient(
        135deg,
        #2f6f6f,
        #1f4e4e
    );
    color: white;
    box-shadow: 0 10px 20px rgba(0,0,0,0.18);
}

/* Click */
.option-btn:active {
    transform: scale(0.95);
}

.user {
    margin-bottom:14px;   /* more breathing space */
}

.bot-row {
    margin-bottom:18px;   /* more gap between bot messages */
}

.chat-header {
    height: 50px;
    background: linear-gradient(135deg, #1f4e4e, #2f6f6f);
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    color: white;
    display:flex;
    align-items:center;
    justify-content: space-between;
    padding: 0 10px;
    font-weight: 600;
}

.header-icon svg {
    transition: transform 0.3s ease;
}

/* Tooltip Wrapper */
.tooltip {
    position: relative;
}

/* Tooltip Text */
.tooltip-text {
    position: absolute;
    bottom: 130%;
    left: 50%;
    transform: translateX(-50%) translateY(5px);
    background: #1f4e4e;
    color: #fff;
    padding: 5px 8px;
    font-size: 11px;
    border-radius: 6px;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

/* Tooltip Arrow */
.tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border-width: 5px;
    border-style: solid;
    border-color: #1f4e4e transparent transparent transparent;
}

/* Show Tooltip */
.tooltip:hover .tooltip-text {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}
/* Bottom Tooltip (for header icons only) */
.tooltip-bottom .tooltip-text {
    top: 50px;  /* same as header height */
    bottom: auto;
    transform: translateX(-50%);
}

.tooltip-bottom .tooltip-text::after {
    top: -10px;
    bottom: auto;
    border-color: transparent transparent #1f4e4e transparent;
}
@keyframes bounce {
    0%,80%,100% { transform:scale(0);}
    40% { transform:scale(1);}
}
/* Floating Animation Container */
.floating-hi {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 55px;
    height: 120px;
    pointer-events: none;
}

/* Hi bubble INSIDE box */
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

/* Hi bubble from chat button */
.chat-hi-bubble {
    position: fixed;
    bottom: 80px;
    right: 20px;
    background: #2f6f6f;
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 13px;
    opacity: 0;
    transform: translateY(10px) scale(0.9);
    transition: all 0.4s ease;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}

/* small tail */
.chat-hi-bubble::after {
    content: "";
    position: absolute;
    bottom: -6px;
    right: 20px;
    border-width: 6px;
    border-style: solid;
    border-color: #2f6f6f transparent transparent transparent;
}

/* Animations */
@keyframes boxRise {
    0% { opacity:0; transform: translateY(20px); }
    100% { opacity:1; transform: translateY(0); }
}

@keyframes boxOpen {
    0% { transform: rotateX(0deg); }
    100% { transform: rotateX(20deg); }
}

@keyframes hiFade {
    0% { opacity:0; transform: translateY(10px); }
    100% { opacity:1; transform: translateY(0); }
}

/*  PREMIUM FLOATING LOGO GLOW */
.chat-button.voice-active {
    animation: premiumPulse 1.6s infinite ease-in-out;
    box-shadow:
        0 0 10px #00f2fe,
        0 0 20px #00c6ff,
        0 0 40px #00f2fe,
        0 0 70px rgba(0,242,254,0.5);
}

/* Smooth breathing animation */
@keyframes premiumPulse {
    0% {
        transform: scale(1);
        box-shadow:
            0 0 5px #00f2fe,
            0 0 15px #00f2fe,
            0 0 30px #00f2fe;
    }
    50% {
        transform: scale(1.08);
        box-shadow:
            0 0 20px #00f2fe,
            0 0 40px #00f2fe,
            0 0 80px rgba(0,242,254,0.8);
    }
    100% {
        transform: scale(1);
        box-shadow:
            0 0 5px #00f2fe,
            0 0 15px #00f2fe,
            0 0 30px #00f2fe;
    }
}
/* Restart rotate animation */
.header-icon.spin svg {
    animation: rotateRestart 0.6s linear;
}

@keyframes rotateRestart {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
/* Keep center title always visible */
.logo-area {
    position: relative;
    z-index: 5;
}

/* Make tooltips lower than title */
.tooltip-text {
    z-index: 2;
}

.options-wrapper {
    display: flex;
    flex-wrap: wrap;
    margin-top: 8px;
}

.bot-typing-row{
    display:flex;
    align-items:flex-end;
    gap:10px;
    margin-bottom:14px;
}

.bot-typing{
    background:#e5e5ea;
    padding:8px 14px;
    border-radius:18px;
    display:inline-flex;
    align-items:center;
    gap:4px;
    box-shadow:0 1px 3px rgba(0,0,0,0.1);
}
</style>
</head>

<body>
<div class="chat-hi-bubble" id="chatHi">
    Hi 👋
</div>

<div class="chat-button" id="chatBtn" onclick="toggleChat()">💬</div>

<div class="chat-box" id="chatBox">

    <div class="chat-header">

        <!-- LEFT RESET ICON -->
        <div class="header-icon tooltip tooltip-bottom" onclick="resetChat(this)">
            <svg viewBox="0 0 24 24">
                <path d="M21 12a9 9 0 1 1-3-6.7"/>
                <polyline points="21 3 21 9 15 9"/>
            </svg>
            <span class="tooltip-text">Restart</span>
        </div>

        <!-- EXISTING CONTENT (UNCHANGED) -->
        <div class="logo-area">
            <div class="box-icon" id="boxIcon">📦</div>
            <div class="hi-text" id="hiText">Hi 👋 Welcome to Photon AI</div>
            <div class="truck-icon" id="truckIcon">🚚</div>
        </div>

        <!-- RIGHT CLOSE ICON -->
        <div class="header-icon tooltip tooltip-bottom" onclick="closeChat()">
            <svg viewBox="0 0 24 24">
                <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
            <span class="tooltip-text">Close</span>
        </div>

    </div>

    <div class="chat-messages" id="messages">

        <div class="bot-row">

            <div class="bot-avatar"></div>

            <div class="bot-content">

                <div class="bot">
                    Hello 👋 {name}! I am your AI Logistics Assistant.
                    Speak English. Say "Hey Photon" to activate voice.
                </div>

                <div class="options-wrapper">

                    <button class="option-btn" onclick="sendOption('create shipment','📦 Create Shipment')">
                        📦 Create Shipment
                    </button>

                    <button class="option-btn" onclick="sendOption('quote','💰 Get Quote')">
                        💰 Get Quote
                    </button>

                    <button class="option-btn" onclick="sendOption('tracking','🚚 Track Shipment')">
                        🚚 Track Shipment
                    </button>

                </div>

            </div>

        </div>
    </div>

    <div class="chat-input">
    <button class="tooltip" onclick="toggleVoice()">
        🎙
        <span class="tooltip-text">Mic</span>
    </button>
        <input type="text" id="messageInput"
        placeholder="Ask about quote or shipment..."
        onkeydown="if(event.key==='Enter'){sendMessage();}">
        <button class="tooltip" onclick="sendMessage()">
            ➤
            <span class="tooltip-text">Send</span>
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

/* HEADER LOOP ANIMATION (unchanged) */
function startHeaderLoop(){
    const box = document.getElementById("boxIcon");
    const hi = document.getElementById("hiText");
    const truck = document.getElementById("truckIcon");

    function run(){
        box.style.opacity = 0;
        hi.style.opacity = 0;
        truck.style.opacity = 0;

        box.style.animation = "none";
        hi.style.animation = "none";
        truck.style.animation = "none";

        void box.offsetWidth;

        box.style.animation = "jumpBox 0.6s forwards";
        setTimeout(()=>{ hi.style.animation = "slideIn 0.6s forwards"; },800);
        setTimeout(()=>{ truck.style.animation = "slideIn 0.6s forwards"; },1200);
        // Wait while fully visible
        setTimeout(()=>{
            hi.style.animation = "smoothErase 1.2s ease forwards";
            truck.style.animation = "smoothErase 1.2s ease forwards";
        },3500);
    }

    run();
    setInterval(run,6000);
}
startHeaderLoop();

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
    messagesDiv.innerHTML += `<div class="user">${message}</div>`;
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

    // 🔥 STEP 2: HANDLE EDIT FORM
    if (data.type === "edit_form") {

        let formDiv = document.createElement("div");
        formDiv.className = "bot";

        let formHTML = `<h4>📝 ${data.title}</h4>`;

        data.fields.forEach(field => {
            formHTML += `
                <div style="margin-bottom:8px;">
                    <label style="font-size:12px;">${field.label}</label><br>
                    <input 
                        type="${field.type}" 
                        id="form_${field.name}" 
                        value="${field.value || ''}"
                        style="width:100%; padding:6px; border-radius:6px; border:1px solid #ccc;"
                    />
                </div>
            `;
        });

        formHTML += `
            <button 
                style="margin-top:10px; padding:8px 12px; background:#2f6f6f; color:white; border:none; border-radius:8px; cursor:pointer;"
                onclick="submitModifyForm()"
            >
                💾 Save & Continue
            </button>
        `;

        formDiv.innerHTML = formHTML;
        messagesDiv.appendChild(formDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        return; // ⛔ STOP normal rendering
    }

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
    botDiv.innerText = data.response || "Something went wrong.";

    content.appendChild(botDiv);

    // Append
    /* OPTIONS */
    if (data.options && data.options.length > 0) {

        let wrapper = document.createElement("div");
        wrapper.className = "options-wrapper";

        data.options.forEach(option => {

            let btn = document.createElement("button");
            btn.className = "option-btn";
            btn.innerText = option.label;

            btn.onclick = function () {
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
    messagesDiv.innerHTML += `<div class="user">${label}</div>`;
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

    if(listening){

        recognition.stop();
        listening=false;

        chatLogo.classList.remove("voice-active");

    }else{

        startVoice();

        chatLogo.classList.add("voice-active");
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
    recognition.start();

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
                Hello 👋 ${USER_NAME}! I am your AI Logistics Assistant.
            </div>

            <div class="options-wrapper">

                <button class="option-btn" onclick="sendOption('create shipment','📦 Create Shipment')">
                    📦 Create Shipment
                </button>

                <button class="option-btn" onclick="sendOption('quote','💰 Get Quote')">
                    💰 Get Quote
                </button>

                <button class="option-btn" onclick="sendOption('tracking','🚚 Track Shipment')">
                    🚚 Track Shipment
                </button>

            </div>

        </div>

    </div>
    `;

    // backend reset
    await fetch("/reset", { method: "POST" });

    setTimeout(()=>{ resetInProgress = false; }, 800);
}

function startHiBubble() {

    const bubble = document.getElementById("chatHi");

    function animate() {

        bubble.style.display = "block";

        bubble.style.opacity = 1;
        bubble.style.transform = "translateY(0) scale(1)";

        setTimeout(() => {
            bubble.style.opacity = 0;
            bubble.style.transform = "translateY(10px) scale(0.9)";
        }, 5000);
    }

    animate();
    hiInterval = setInterval(animate, 8000);
}

startHiBubble();

/* Modify Form Submission */
async function submitModifyForm() {

    let inputs = document.querySelectorAll("[id^='form_']");
    let formData = {};

    inputs.forEach(input => {
        let key = input.id.replace("form_", "");
        formData[key] = input.value;
    });

    showTyping();

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: "submit_modify_form:" + JSON.stringify(formData)
        })
    });

    let data = await response.json();
    removeTyping();
    renderBotResponse(data);
}
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