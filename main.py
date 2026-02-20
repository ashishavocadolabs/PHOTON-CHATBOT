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
body { font-family: 'Segoe UI', sans-serif; }

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
}

/* Header */
.chat-header {
    background: linear-gradient(135deg, #007bff, #0056b3);
    color: white;
    padding: 15px;
    font-weight: bold;
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
    white-space: pre-line;
}

.user {
    background: #007bff;
    color: white;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 8px;
    margin-left: auto;
    max-width: 80%;
}

/* Input */
.chat-input {
    display: flex;
    padding: 10px;
    border-top: 1px solid #eee;
}

.chat-input input {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #ccc;
}

.chat-input button {
    margin-left: 6px;
    padding: 10px 14px;
    border-radius: 8px;
    border: none;
    background: #007bff;
    color: white;
    cursor: pointer;
}

.option-btn {
    margin: 6px 0;
    padding: 10px;
    border-radius: 10px;
    border: none;
    cursor: pointer;
    background: #e4e6eb;
    width: 100%;
    text-align: left;
    transition: 0.2s;
}

.option-btn:hover {
    background: #d8dbe0;
}
</style>
</head>

<body>

<div class="chat-button" onclick="toggleChat()">💬</div>

<div class="chat-box" id="chatBox">
    <div class="chat-header">
        Photon AI Logistics Assistant 🚀
    </div>

    <div class="chat-messages" id="messages">
        <div class="bot">Hi 👋 How can I help you today?</div>
    </div>

    <div class="chat-input">
        <input type="text" id="messageInput"
        placeholder="Ask about quote or tracking..."
        onkeydown="if(event.key==='Enter'){sendMessage();}">
        <button onclick="sendMessage()">Send</button>
    </div>
</div>

<script>

function toggleChat() {
    let box = document.getElementById("chatBox");
    box.style.display = box.style.display === "flex" ? "none" : "flex";
    box.style.flexDirection = "column";
}

async function sendOption(value, label) {

    let messagesDiv = document.getElementById("messages");

    // Show selected label (NOT number)
    messagesDiv.innerHTML += `<div class="user">✅ Selected: ${label}</div>`;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: value })
    });

    let data = await response.json();
    renderBotResponse(data);
}

async function sendMessage() {

    let input = document.getElementById("messageInput");
    let message = input.value.trim();
    if (!message) return;

    let messagesDiv = document.getElementById("messages");

    messagesDiv.innerHTML += `<div class="user">${message}</div>`;
    input.value = "";
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    let response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    });

    let data = await response.json();
    renderBotResponse(data);
}

function renderBotResponse(data) {

    let messagesDiv = document.getElementById("messages");

    let botDiv = document.createElement("div");
    botDiv.className = "bot";
    botDiv.innerText = data.response || "Something went wrong.";
    messagesDiv.appendChild(botDiv);

    // Create option buttons (do NOT remove old content)
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

</script>

</body>
</html>
"""


@app.post("/chat")
async def chat(request: ChatRequest):
    return handle_chat(request.message)