from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.ai_orchestrator import handle_chat, reset_state
from services.auth_service import get_logged_user_name

app = FastAPI()

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
    font-family: 'Segoe UI', sans-serif;
}

/* Floating Button */
.chat-button {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #2f6f6f;
    color: white;
    border-radius: 50%;
    width: 55px;
    height: 55px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 22px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    transition: 0.3s;
}
.chat-button:hover {
    transform: scale(1.05);
}
.chat-button.listening {
    background:#c0392b;
}

/* Chat Box */
.chat-box {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 360px;
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

/* Messages Area */
.chat-messages {
    flex:1;
    padding:15px;
    overflow-y:auto;
    background:#f4f6f8;
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
.header-icon {
    width:32px;
    height:32px;
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    border-radius:8px;
    transition:0.3s;
}

.header-icon svg {
    width:18px;
    height:18px;
    fill:white;
    stroke:white;
    stroke-width:2;
}

.header-icon:hover {
    background:rgba(255,255,255,0.15);
    transform:scale(1.1);
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

@keyframes swipeOut {
    from { transform: translateX(0); opacity:1; }
    to { transform: translateX(120%); opacity:0; }
}

/* Messages */
.chat-messages {
    flex:1;
    padding:15px;
    overflow-y:auto;
    background:#0f2027;
    color:white;
}

/* Bot Message */
.bot {
    background:#ffffff;
    padding:10px 14px;
    border-radius:12px;
    margin-bottom:10px;
    font-size:14px;
    box-shadow:0 2px 6px rgba(0,0,0,0.05);
    border-left:4px solid #2f6f6f;
}

/* User Message */
.user {
    background:#2f6f6f;
    color:white;
    padding:10px 14px;
    border-radius:12px;
    margin-bottom:10px;
    margin-left:auto;
    font-size:14px;
    max-width:80%;
}


@keyframes fadeIn {
    from{opacity:0; transform:translateY(10px);}
    to{opacity:1; transform:translateY(0);}
}

.bot {
    background:#1e2a38;
    border:1px solid #00f2fe;
}

.user {
    background:#00f2fe;
    color:black;
    margin-left:auto;
}

/* Typing */
.typing span {
    height:8px;
    width:8px;
    background:#00f2fe;
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
    background:#00f2fe;
    color:black;
    padding:10px 14px;
    border-radius:12px;
    margin-bottom:10px;
    margin-left:auto;
    font-size:14px;
    max-width:80%;
    display:flex;
    align-items:center;
    gap:6px;
    opacity:0.8;
}

/* Animated dots */
.sending span {
    width:6px;
    height:6px;
    background:black;
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
.option-btn {
    display:block;
    width:100%;
    text-align:left;
    margin-top:6px;
    padding:8px 10px;
    border-radius:8px;
    border:1px solid #dcdcdc;
    background:#ffffff;
    cursor:pointer;
    font-size:13px;
}
.option-btn:hover {
    background:#f0f7f7;
}

/* Typing Animation */
.typing span {
    height:6px;
    width:6px;
    background:#2f6f6f;
    border-radius:50%;
    display:inline-block;
    margin:0 2px;
    animation:bounce 1.4s infinite;
}
.typing span:nth-child(2){animation-delay:0.2s;}
.typing span:nth-child(3){animation-delay:0.4s;}

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
    top: 120%;
    bottom: auto;
    transform: translateX(-50%) translateY(-5px);
}

.tooltip-bottom .tooltip-text::after {
    top: auto;
    bottom: 100%;
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
    bottom: 85px;
    right: 20px;
    background: #2f6f6f;
    color: white;
    padding: 6px 14px;
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
        <div class="header-icon tooltip tooltip-bottom" onclick="resetChat()">
            <svg viewBox="0 0 24 24">
                <path d="M12 6V3L8 7l4 4V8c2.76 0 5 2.24 5 5a5 5 0 11-5-5z"/>
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
        <div class="bot">Hello 👋 {name}! I am your AI Logistics Assistant. Speak Hindi or English. Say "Hey Photon" to activate voice.</div>
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

/* Toggle Chat */
function toggleChat() {
    let box = document.getElementById("chatBox");

    if(box.classList.contains("active")){
        box.classList.remove("active");
        setTimeout(()=>{ box.style.display="none"; },300);
    } else {
        box.style.display="flex";
        setTimeout(()=>{ box.classList.add("active"); },10);
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
        setTimeout(()=>{
            hi.style.animation = "swipeOut 0.8s forwards";
            truck.style.animation = "swipeOut 0.8s forwards";
        },3000);
    }

    run();
    setInterval(run,6000);
}
startHeaderLoop();

/* Typing Indicator */
function showTyping(){
    let messagesDiv = document.getElementById("messages");
    let typingDiv = document.createElement("div");
    typingDiv.className = "bot";
    typingDiv.id = "typing";
    typingDiv.innerHTML = `<div class="typing">
        <span></span><span></span><span></span>
    </div>`;
    messagesDiv.appendChild(typingDiv);
}

function removeTyping(){
    let typingDiv = document.getElementById("typing");
    if(typingDiv) typingDiv.remove();
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

    let botDiv = document.createElement("div");
    botDiv.className = "bot";
    botDiv.innerText = data.response || "Something went wrong.";
    messagesDiv.appendChild(botDiv);

    if(listening){
        speakText(data.response);
    }

    if (data.options && data.options.length > 0) {
        data.options.forEach(option => {
            let btn = document.createElement("button");
            btn.className = "option-btn";
            btn.innerText = option.label;
            btn.onclick = function () {
                sendOption(option.value, option.label);
            };
            messagesDiv.appendChild(btn);
        });
    }

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendOption(value, label) {
    let messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML += `<div class="user">✅ ${label}</div>`;
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

/* ================= VOICE SYSTEM ================= */

let recognition;
let listening=false;
let wakeWord="hey photon";

function toggleVoice(){
    if(listening){
        recognition.stop();
        listening=false;
        document.getElementById("chatBtn").classList.remove("listening");
    }else{
        startVoice();
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

async function resetChat(){

    // stop voice if active
    if(recognition && listening){
        recognition.stop();
        listening = false;
        document.getElementById("chatBtn").classList.remove("listening");
    }

    // clear UI
    let messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML = `
        <div class="bot">
            Hello 👋 ${USER_NAME} I am your AI Logistics Assistant.
        </div>
    `;

    // optional backend reset
    await fetch("/reset", { method: "POST" });

    document.querySelector(".header-icon svg").style.transform = "rotate(360deg)";
    setTimeout(()=>{
        document.querySelector(".header-icon svg").style.transform = "rotate(0deg)";
    },300);
}

function startHiBubble() {
    const bubble = document.getElementById("chatHi");

    function animate() {

        // Show
        bubble.style.opacity = 1;
        bubble.style.transform = "translateY(0) scale(1)";

        // Hide after 5 sec
        setTimeout(() => {
            bubble.style.opacity = 0;
            bubble.style.transform = "translateY(10px) scale(0.9)";
        }, 5000);
    }

    animate();
    setInterval(animate, 8000);
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