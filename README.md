# 🚀 PHOTON – AI Powered Logistics & Shipping Management System

**A modular AI-powered Backend Logistics System, built with scalable architecture to manage shipping quotations, shipment tracking, authentication workflows, and intelligent request orchestration using a centralized AI engine.

## 🎯 Key Features
### 🤖 AI Orchestration Engine

* Intelligent request routing

* Intent detection (Shipping / Tracking / Authentication)

* Modular service invocation

* Extensible NLP-ready structure

* Centralized decision-making system

### 📦 Shipping Quotation System

* Calculate shipping rates using:

* From Pincode

* To Pincode

* Weight

* Dimensions
 
* Dynamic pricing logic

* Distance-based calculation ready

* Future ML-based pricing prediction support

### 🚚 Shipment Tracking

* Track shipment using tracking ID

* Retrieve shipment status

* Delivery timeline updates

* Extendable for real-time courier API integration

### 🔐 Authentication System

* Secure login validation

* Token-based access control

* Environment-based secret configuration

* Modular authentication service

### 🏗️ Technical Architecture
* Backend (Python Modular Architecture)

* Python 3.x

* Service-based architecture

* AI Orchestrator core engine

* Environment variable configuration

* Scalable modular design

### 🧠 System Flow Architecture
* User Request
      ↓
* main.py (Entry Point)
      ↓
* AI Orchestrator
      ↓
* Service Layer (Shipping / Tracking / Auth)
      ↓
* Response Returned
### 📁 Project Structure
```
PHOTON/
│
├── core/
│   ├── __pycache__/
│   ├── ai_orchestrator.py
│   ├── rag_engine.py               # RAG / memory logic (documents & conversation)
│
├── pipelines/                      # helper code for chunking/embeddings/ingest
│   ├── chunking.py
│   ├── embeddings.py
│   └── ingestion_pipeline.py
│
├── retrieval/                      # vector store implementations
│   ├── vector_store.py
│   └── bm25_index.py
│
├── models/
│   └── (Future: DB models / schemas)
│
├── services/
│   ├── __pycache__/
│   ├── auth_service.py
│   └── shipping_service.py
│
├── tools/
│   ├── __pycache__/
│   └── tracking_shipment.py
│
├── knowledge/                      # documents used by the RAG engine
│   └── photon_docs/
│
├── venv/
├── .env
├── main.py
└── README.md
```
### 🗄️ Architecture Design Principles

* Clean separation of concerns

* Modular service structure

### 🔊 Voice & transcription

The front‑end relies on the browser's Web Speech API for voice
recognition and text‑to‑speech.  Server‑side transcription support has
been removed for simplicity; the `/voice` route has been eliminated
entirely, and no audio is posted to the server any more.  The previous
implementation used OpenAI Whisper and required `python-multipart`;
those dependencies are no longer needed.  Only a single microphone
button (the blue chat button) is used for voice interaction – the
former "record audio" icon was removed.

A separate feature allows server‑side **text‑to‑speech** using ElevenLabs
audio.  Specify `ELEVENSLAB_API` in `.env` (optionally also
`ELEVEN_VOICE_ID` to pick a non‑default voice).  The code now defaults to
a male voice ID – change the variable if you prefer a female or other
characteristic.  When present the browser client will request `/speak`
for each bot response and play the returned audio; if the endpoint is
unavailable or fails, the normal `SpeechSynthesisUtterance` fallback is
used.

The existing *voice fuzzy matching* logic has been extended so that
warehouse, ship‑to and courier/service names are all matched against
spoken text, a hint is shown with the full name/description, and the
user is asked to confirm before the value is accepted.

* Extendable AI layer (now includes retrieval‑augmented generation & conversational memory)

* Scalable folder organization

* Environment-based configuration

* Production-ready layout

### 🚀 Quick Commands
* Run Application
* python main.py
* Create Virtual Environment
* python -m venv venv

* Activate:

* Windows:

* venv\Scripts\activate

* Mac/Linux:

* source venv/bin/activate
* Install Dependencies
* pip install -r requirements.txt
###  🛠️ Getting Started
* Prerequisites

* Python 3.10+

* pip

* Virtual Environment

* (Optional) FastAPI / Flask if extended to API

* Clone Repository
* git clone https://github.com/yourusername/PHOTON.git
* cd PHOTON
* Setup Environment Variables (.env)
* API_KEY=your_api_key
* USER_ID=your_photon_id
* Password=your_photon_password

* **New for RAG**: install numeric and vector libraries
```bash
pip install numpy faiss-cpu  # faiss optional; you can remove or replace with sklearn
```

### 🧠 Retrieval‑Augmented Generation (RAG) & Memory

A new ``core/rag_engine.py`` module powers a simple RAG system backed by the
``knowledge/photon_docs`` directory.  Documents are chunked, embedded and stored
in a lightweight on‑disk vector index; user messages are also recorded to a
separate memory index so that the assistant can recall earlier turns.

#### Indexing your documents

Run the following from a Python REPL or a one‑line script:

```python
from pipelines.ingestion_pipeline import ingest_directory
# rebuild the index (takes a few seconds for large corpora)
ingest_directory("knowledge/photon_docs", "rag_index.pkl")
```

The ``rag_index.pkl`` and ``memory_index.pkl`` files will appear in the repo
root.  They are used automatically by the assistant; you can periodically
re‑run the ingestion step after adding new information to ``photon_docs``.

#### How it affects the chat flow

When the chat handler receives a message it first asks ``rag_engine`` for an
answer.  If the query matches something in the index the retrieved text is
prepended to the prompt and the LLM will generate a fact‑based response.  If
no relevant documents or memories exist the system falls back to the original
shipping‑only behaviour.

The memory store automatically records every user utterance and every RAG
response, so follow‑up questions like "what did I just ask you about the
warehouse rules?" will work naturally.

The core handler remains unchanged; however, a lightweight agent wrapper has
been added in ``core/agent.py`` which exposes the same functionality via an
"agentic" interface (perceive/plan/act).  The current implementation provides
several built‑in enhancements:

* **Retrieval‑first planning (with escape hatch)** – the agent consults the
  document index before invoking the shipping logic, but it first checks for a
  logistics intent or an ongoing flow.  Queries like "I want to ship" or
  "get quote" now bypass RAG and trigger the usual APIs immediately, preventing
  the documentation from hijacking the conversation.
* **State persistence** – conversation state is written to
  ``agent_state.json`` after every turn and reloaded on startup, enabling
  longer lived interactions or restarts without losing context.

This design makes it easy to layer further behaviour such as multi‑step
reasoning, scheduled triggers, or external tool orchestration while keeping
the original chat logic untouched.

``main.py`` now defaults to routing incoming messages through
``chat_agent.handle_message``; code elsewhere can continue to call
``core.ai_orchestrator.handle_chat`` directly if preferred.

#### 🎭 Service Modules
#### 📦 Shipping Service

* Cost calculation logic

* Delivery estimation

* Extendable to:

* ML dynamic pricing

* Courier selection AI

* Distance-based rate logic

### 🚚 Tracking Tool

* Shipment tracking

* Status monitoring

* API-ready integration design