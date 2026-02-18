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
    font-family: 'Segoe UI', sans-serif;
}

/* Floating Button */
.chat-button {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: linear-gradient(135deg, #007bff, #0056b3);
    color: white;
    border-radius: 50%;
    width: 65px;
    height: 65px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 26px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    transition: 0.3s;
}

.chat-button:hover {
    transform: scale(1.1);
}

/* Hi Badge */
.hi-badge {
    position: absolute;
    top: -28px;
    right: 0;
    background: #ff4757;
    color: white;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 12px;
    animation: zigzag 1.2s infinite;
}

@keyframes zigzag {
    0% { transform: translateX(0); }
    25% { transform: translateX(-5px); }
    50% { transform: translateX(5px); }
    75% { transform: translateX(-3px); }
    100% { transform: translateX(0); }
}

/* Chat Box */
.chat-box {
    position: fixed;
    bottom: 100px;
    right: 20px;
    width: 360px;
    height: 520px;
    background: white;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    display: none;
    flex-direction: column;
    overflow: hidden;
    animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Header */
.chat-header {
    background: linear-gradient(135deg, #007bff, #0056b3);
    color: white;
    padding: 15px;
    font-weight: bold;
    font-size: 15px;
}

/* Messages */
.chat-messages {
    flex: 1;
    padding: 12px;
    overflow-y: auto;
    background: #f4f6f9;
}

.bot {
    background: #e4e6eb;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
    max-width: 100%;
    font-size: 14px;
    white-space: pre-line;
    line-height: 1.6;
    word-wrap: break-word;
}

.user {
    background: #007bff;
    color: white;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 8px;
    margin-left: auto;
    max-width: 80%;
    font-size: 14px;
}

/* Typing Animation */
.typing {
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
}

.dot {
    width: 6px;
    height: 6px;
    background: gray;
    border-radius: 50%;
    animation: blink 1.4s infinite both;
}

.dot:nth-child(2) {
    animation-delay: 0.2s;
}

.dot:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes blink {
    0% { opacity: .2; }
    20% { opacity: 1; }
    100% { opacity: .2; }
}

/* Input Area */
.chat-input {
    display: flex;
    padding: 10px;
    border-top: 1px solid #eee;
    background: white;
}

.chat-input input {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #ccc;
    font-size: 14px;
}

.chat-input button {
    margin-left: 6px;
    padding: 10px 14px;
    border-radius: 8px;
    border: none;
    background: #007bff;
    color: white;
    cursor: pointer;
    transition: 0.2s;
}

.chat-input button:hover {
    background: #0056b3;
}

</style>
</head>

<body>

<div class="chat-button" onclick="toggleChat()">
    💬
    <div class="hi-badge" id="hiBadge">Hi 👋</div>
</div>

<div class="chat-box" id="chatBox">
    <div class="chat-header">
        Photon AI Logistics Assistant 🚀
    </div>

    <div class="chat-messages" id="messages">
        <div class="bot">Hi 👋 How can I help you today?</div>
    </div>

    <div class="chat-input">
        <input type="text" id="messageInput" placeholder="Ask about quote or tracking..."
        onkeydown="if(event.key==='Enter'){sendMessage();}">
        <button onclick="sendMessage()">Send</button>
    </div>
</div>

<script>

function toggleChat() {
    let box = document.getElementById("chatBox");
    let badge = document.getElementById("hiBadge");

    if (box.style.display === "flex") {
        box.style.display = "none";
        badge.style.display = "block";
    } else {
        box.style.display = "flex";
        box.style.flexDirection = "column";
        badge.style.display = "none";
    }
}

async function sendMessage() {
    let input = document.getElementById("messageInput");
    let message = input.value.trim();
    if (!message) return;

    let messagesDiv = document.getElementById("messages");

    messagesDiv.innerHTML += `<div class="user">${message}</div>`;
    input.value = "";
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Typing animation
    let typing = document.createElement("div");
    typing.className = "typing";
    typing.id = "typing";
    typing.innerHTML = "<div class='dot'></div><div class='dot'></div><div class='dot'></div>";
    messagesDiv.appendChild(typing);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    });

    let data = await response.json();

    document.getElementById("typing").remove();

    let botReply = data.response || "Something went wrong.";

    messagesDiv.innerHTML += `<div class="bot">${botReply}</div>`;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

</script>

</body>
</html>
"""


@app.post("/chat")
async def chat(request: ChatRequest):
    return handle_chat(request.message)