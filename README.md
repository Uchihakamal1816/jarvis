# 🤖 Project JARVIS — Voice-First Multi-Agent Assistant

[![Built With Claude AI](https://img.shields.io/badge/Built%20With-Claude%20AI-7A42F4?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![Google Antigravity SDK](https://img.shields.io/badge/Orchestration-Google%20Antigravity-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Groq LPU](https://img.shields.io/badge/Spoken%20LLM-Groq%20LPU-FF6F00?style=for-the-badge&logo=fastapi&logoColor=white)](https://groq.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

**Project JARVIS** is a voice-first autonomous AI assistant powered by the **Hermes Orchestration Layer** using the **Google Antigravity Python SDK**, **Groq LPU speed summarization**, and low-latency voice pipeline tools (Silero VAD + faster-whisper + Edge-TTS).

> 💡 **Collaborator Note**: Project JARVIS was engineered in pair-programming collaboration with **Claude AI** (`claude-code`), which architected the Hermes orchestration layer, subagent hierarchy, rate-limit safeguards, and real-time voice pipeline optimizations.

---

## 🏛️ System Architecture

```
                       ┌─────────────────────────┐
                       │     USER VOICE INPUT    │
                       └────────────┬────────────┘
                                    │ (Silero VAD 500ms + faster-whisper)
                       ┌────────────▼────────────┐
                       │  Thinking Quote Engine  │ 🔊 Speaks 1 of 200 Stoic/Power
                       └────────────┬────────────┘    quotes while LLM computes
                                    │
                       ┌────────────▼────────────┐
                       │   Supervisor Agent      │ (Hermes Layer: gemini-3.5-flash-lite)
                       └────────────┬────────────┘
         ┌──────────────────┬───────┴──────────┬──────────────────┐
         │                  │                  │                  │
┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
│ System Admin    │ │ Research Agent │ │  Coding Agent  │ │ Browser Agent  │
│ (PC Metrics,    │ │ (Web Search)   │ │ (File Inspect) │ │ (Web Nav)      │
│  SSH, Folders)  │ └────────────────┘ └────────────────┘ └────────────────┘
└────────┬────────┘
         └──────────────────┬─────────────────────────────────────┘
                                    │ (Raw Multi-Agent Output)
                       ┌────────────▼────────────┐
                       │ Groq Voice Improviser   │ ⚡ Summarizes into 1-2 crisp
                       └────────────┬────────────┘    spoken sentences (qwen3.8-27b)
                                    │
                       ┌────────────▼────────────┐
                       │   TTS Voice Output      │ 🔊 Edge-TTS (en-GB-ThomasNeural)
                       └─────────────────────────┘    + pyttsx3 offline fallback
```

---

## 🤖 Active Agent Roster

| # | Agent Name | Role | Allowed Tools | Description |
| :-: | :--- | :--- | :--- | :--- |
| 🛡️ **1** | **Supervisor Agent** | Root Master Intelligence | `gemini-3.5-flash-lite` | Master coordinator that receives voice prompts, formulates execution plans, and delegates to specialized subagents. |
| ⚡ **2** | **System Admin Agent** (`sys_admin_agent`) | Subagent | `RUN_COMMAND`, `VIEW_FILE`, `LIST_DIR`, `SEARCH_DIR`, `FIND_FILE` | Checks PC system metrics (CPU, RAM, disk, uptime), verifies SSH health, searches PC folders, and reads code files across directories. |
| 🔍 **3** | **Research Agent** (`research_agent`) | Subagent | `SEARCH_WEB` | Researches web information, technical documentation, and online queries. |
| 💻 **4** | **Coding Agent** (`coding_agent`) | Subagent | `VIEW_FILE` | Inspects, reads, and analyzes local code files and project structures. |
| 🌐 **5** | **Browser Agent** (`browser_agent`) | Subagent | Web Navigation | Specialist configured for web interface and web page interactions. |
| 🚀 **6** | **Groq Voice Improviser** | Spoken Voice Layer | Groq LPU (`qwen/qwen3.8-27b`) | Post-processes raw agent outputs, condensing them into 1-2 ultra-crisp, spoken sentences. |

---

## ✨ Key Features

- ⚡ **Low-Latency Voice Pipeline**: 500ms Silero VAD silence cutoff and `faster-whisper` STT for rapid utterance detection.
- 💡 **Thinking Quote Engine**: Speaks a random motivational/philosophical quote from a curated bank of 200 self-growth, wealth, and power quotes while Hermes computes, masking silent waiting time.
- 🔋 **API Battery Meter**: Instant voice status trigger (`"JARVIS, how much battery is left?"`) returning sliding 60-second window API quotas for Gemini and Groq.
- 📂 **PC Folder & Code Reading**: System Admin Agent searches PC directories, finds files by name, and inspects codebase contents autonomously.
- 🔊 **Markdown Speech Sanitizer & Offline Fallback**: Strips formatting symbols (`**`, `#`, backticks) for natural speech delivery, backed by a local `pyttsx3` offline TTS engine if network connection drops.

---

## ⚙️ Environment & Installation Setup

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/Uchihakamal1816/jarvis.git
cd jarvis
```

### 2. Configure API Keys (`.env`)

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

```env
# Google Antigravity SDK
GEMINI_API_KEY=your_gemini_api_key_here

# Groq LLM (Voice Improviser)
GROQ_API_KEY=your_groq_api_key_here

# Claude AI (Anthropic Integration)
ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 3. Create Virtual Environment & Install Dependencies

```bash
python3 -m venv voice/.venv
source voice/.venv/bin/activate
pip install -r voice/requirements.txt
```

---

## 🚀 Running JARVIS Live

Start the live microphone listening loop:

```bash
export OUTPUT_MODE=core
voice/.venv/bin/python -m voice.src.main
```

### Voice Commands to Try:
- 🎙️ *"Hi JARVIS, can you check my laptop utils?"*
- 🎙️ *"Search for Python files in my Desktop folder."*
- 🎙️ *"How much API battery is left?"*
- 🎙️ *"Explain the theory of relativity."*

---

## 👥 Authors & Collaborator Credits

- **Kamal Nannuri** ([@Uchihakamal1816](https://github.com/Uchihakamal1816)) — Project Creator & Lead Developer.
- **Claude AI** ([Anthropic](https://anthropic.com)) — Co-Author & Autonomous AI Agent Pair-Programmer (`claude-code`).
