from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.ai_orchestrator import handle_chat

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Photon AI Assistant</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body {
    margin:0;
    font-family: 'Segoe UI', sans-serif;
    background: radial-gradient(circle at top, #0f2027, #203a43, #2c5364);
}

/* Floating Button */
.chat-button {
    position: fixed;
    bottom: 25px;
    right: 25px;
    background: linear-gradient(135deg,#00f2fe,#4facfe);
    color: white;
    border-radius: 50%;
    width: 70px;
    height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 28px;
    box-shadow: 0 0 20px #00f2fe;
}

/* Chat Box */
.chat-box {
    position: fixed;
    bottom: 110px;
    right: 25px;
    width: 400px;
    height: 600px;
    background: rgba(10,20,30,0.95);
    border-radius: 20px;
    box-shadow: 0 0 30px #00f2fe;
    display: none;
    flex-direction: column;
    overflow: hidden;
}

/* HEADER */
.chat-header {
    height: 80px;
    background: linear-gradient(90deg,#00f2fe,#4facfe);
    position: relative;
    overflow:hidden;
}

/* ===== LOGO ANIMATION AREA ===== */
.logo-area {
    position: relative;
    height: 100%;
}

/* Box */
.box-icon {
    position: absolute;
    left: 20px;
    top: 25px;
    font-size: 26px;
    opacity: 0;
}

/* Hi Text */
.hi-text {
    position: absolute;
    left: 65px;
    top: 28px;
    font-weight: bold;
    font-size: 16px;
    white-space: nowrap;
    opacity: 0;
}

/* Truck */
.truck-icon {
    position: absolute;
    right: 20px;
    top: 25px;
    font-size: 26px;
    opacity: 0;
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

.bot, .user {
    padding:12px;
    border-radius:15px;
    margin-bottom:10px;
    white-space: pre-line;
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

/* Input */
.chat-input {
    display:flex;
    padding:12px;
    background:#16222a;
}

.chat-input input {
    flex:1;
    padding:10px;
    border-radius:10px;
    border:none;
    outline:none;
}

.chat-input button {
    margin-left:8px;
    padding:10px 15px;
    border-radius:10px;
    border:none;
    background:#00f2fe;
    cursor:pointer;
}

/* Options */
.option-btn {
    margin:6px 0;
    padding:10px;
    border-radius:10px;
    border:none;
    background:#1e2a38;
    color:white;
    border:1px solid #00f2fe;
    cursor:pointer;
}
.option-btn:hover {
    background:#00f2fe;
    color:black;
}
</style>
</head>

<body>

<div class="chat-button" onclick="toggleChat()">💬</div>

<div class="chat-box" id="chatBox">

    <div class="chat-header">
        <div class="logo-area">
            <div class="box-icon" id="boxIcon">📦</div>
            <div class="hi-text" id="hiText">Hi 👋 Welcome to Photon AI</div>
            <div class="truck-icon" id="truckIcon">🚚</div>
        </div>
    </div>

    <div class="chat-messages" id="messages">
        <div class="bot">Hello 👋 I am your AI Logistics Assistant. How can I help you today?</div>
    </div>

    <div class="chat-input">
        <input type="text" id="messageInput"
        placeholder="Ask about quote or tracking..."
        onkeydown="if(event.key==='Enter'){sendMessage();}">
        <button onclick="sendMessage()">Send</button>
    </div>

</div>

<script>

/* Toggle Chat */
function toggleChat() {
    let box = document.getElementById("chatBox");
    box.style.display = box.style.display === "flex" ? "none" : "flex";
    box.style.flexDirection = "column";
}

/* ===== HEADER LOOP ANIMATION ===== */
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

        // Box Jump
        box.style.animation = "jumpBox 0.6s forwards";

        // Hi Show
        setTimeout(()=>{
            hi.style.animation = "slideIn 0.6s forwards";
        },800);

        // Truck Show
        setTimeout(()=>{
            truck.style.animation = "slideIn 0.6s forwards";
        },1200);

        // Swipe Remove
        setTimeout(()=>{
            hi.style.animation = "swipeOut 0.8s forwards";
            truck.style.animation = "swipeOut 0.8s forwards";
        },3000);

    }

    run();
    setInterval(run,6000);
}

startHeaderLoop();

/* ===== CHAT FUNCTIONS ===== */

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

async function sendMessage() {

    let input = document.getElementById("messageInput");
    let message = input.value.trim();
    if (!message) return;

    let messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML += `<div class="user">${message}</div>`;
    input.value = "";
    showTyping();

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    });

    let data = await response.json();
    removeTyping();
    renderBotResponse(data);
}

function renderBotResponse(data) {

    let messagesDiv = document.getElementById("messages");

    let botDiv = document.createElement("div");
    botDiv.className = "bot";
    botDiv.innerText = data.response || "Something went wrong.";
    messagesDiv.appendChild(botDiv);

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

</script>

</body>
</html>
"""

@app.post("/chat")
async def chat(request: ChatRequest):
    return handle_chat(request.message)