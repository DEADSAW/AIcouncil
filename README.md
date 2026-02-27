# ⚖️ AI Council — Multi-Agent Debate System

AI Council is a web-based application where multiple AI agents **debate, argue, critique, and vote** on answers to your questions. Each agent is powered by a different free-tier LLM API (Groq, Google Gemini, OpenRouter, Cerebras, Cohere), giving you a diverse set of perspectives.

---

## What Does It Do?

1. You type a question in the browser.
2. **Thinker 1** proposes an initial answer.
3. **Thinker 2 (Critic)** challenges it, finds flaws, and proposes alternatives.
4. **Thinker 1** revises based on the criticism.
5. **Thinker 2** re-evaluates the revision.
6. The **Judge** reviews the full debate and gives a final verdict.
7. All agents **vote**: APPROVE / REJECT / NEEDS REVISION.
8. A "Council-Approved" decision is displayed.

---

## Screenshots

```
┌─────────────────────────────────────────────────────┐
│ ⚖️ AI Council — Multi-Agent Debate                   │
│                                                     │
│  Your question: [______________________________]    │
│                                        [🚀 Debate!] │
│                                                     │
│  💡 Thinker 1 · Initial Proposal                    │
│  ────────────────────────────────────────────────   │
│  Here is my proposed solution...                    │
│                                                     │
│  🔍 Thinker 2 (Critic) · Critique                   │
│  ────────────────────────────────────────────────   │
│  I disagree because...                              │
│                                                     │
│  ⚖️ Judge · Final Verdict                            │
│  ────────────────────────────────────────────────   │
│  After reviewing both sides...                      │
│                                                     │
│  🗳️ Council Vote: APPROVE: 2/3 | REJECT: 0/3        │
│  ✅ Council Approved Solution                       │
└─────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.11 or newer** ([download here](https://www.python.org/downloads/))
- **Free API keys** (see below — all are free-tier)

---

## Step-by-Step Setup

### 1. Get your free API keys

| Provider | Signup Link | Notes |
|---|---|---|
| **Groq** | https://console.groq.com | Free tier, very fast |
| **Google AI Studio** | https://aistudio.google.com | Gemini 2.0 Flash, free |
| **OpenRouter** | https://openrouter.ai | Free models available |
| **Cerebras** | https://cloud.cerebras.ai | Free tier |
| **Cohere** | https://dashboard.cohere.com | Free trial key |

You only need **at least one** key to get started. The system works best with all three default providers (Groq + Google + OpenRouter).

### 2. Clone / download this project

```bash
git clone https://github.com/DEADSAW/AIcouncil.git
cd AIcouncil
```

### 3. Create a virtual environment

```bash
# On macOS / Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create your `.env` file

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

Open `.env` in a text editor and replace the placeholder values:

```
GROQ_API_KEY=gsk_your_actual_key_here
GOOGLE_API_KEY=your_actual_google_key_here
OPENROUTER_API_KEY=sk-or-v1-your_actual_key_here
CEREBRAS_API_KEY=csk-your_actual_key_here
COHERE_API_KEY=your_actual_cohere_key_here
```

> ⚠️ **Never commit your `.env` file to Git.** It is already listed in `.gitignore`.

### 6. Run the app

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.

---

## How to Use the Web UI

1. **Type your question** in the text box at the top.
2. *(Optional)* Expand **"Attach files or URLs"** to upload files or paste links for additional context.
3. Click **🚀 Debate!**
4. Watch the agents debate in real time — each agent's response appears with their name, role, and which AI model they used.
5. After the debate, see the **voting results** and the final **Council-Approved Solution**.

### Attaching Files

- Supported formats: `.txt`, `.py`, `.js`, `.ts`, `.md`, `.json`, `.csv`, `.pdf`, `.html`, `.yaml`, and more.
- Maximum file size: 10 MB per file.
- For PDFs, text is automatically extracted.

### Attaching URLs

- Paste one URL per line. The app will fetch and include the page content as context.

---

## How to Add New Agents

1. Open the **sidebar** on the left.
2. Click **"Configure new agent"** to expand the form.
3. Fill in:
   - **Agent name** — e.g. "Security Expert"
   - **Role** — Thinker, Critic, Judge, Researcher, or Security Auditor
   - **Provider** — which AI service to use
   - **Model** — which model from that provider
4. Click **"Add to Council"**.

The new agent will immediately participate in the next debate.

To **remove an agent**, click the **✕** button next to their name in the sidebar.

---

## Project Structure

```
AIcouncil/
├── .env.example      # Template for API keys (fill this in → save as .env)
├── .gitignore        # Keeps .env out of Git
├── requirements.txt  # Python dependencies
├── README.md         # This file
├── app.py            # Main Streamlit app (entry point)
├── providers.py      # LLM provider clients (Groq, Google, OpenRouter, Cerebras, Cohere)
├── agents.py         # Agent definitions, system prompts, role management
├── rate_limiter.py   # Per-provider rate limiting with automatic fallback
├── debate.py         # Debate orchestration and voting system
├── file_handler.py   # File upload processing and URL fetching
└── config.py         # Provider configs, agent defaults, constants
```

---

## Adding a New Provider

1. Add a new entry to the `PROVIDERS` dict in `config.py`.
2. If it's OpenAI-compatible, set `"type": "openai_compatible"` — no other changes needed.
3. If it uses a custom API, add a `_chat_<provider>` function in `providers.py` and register it in the `chat()` dispatch function.

---

## Rate Limiting

The sidebar shows live rate limit usage for each provider. If a provider is rate-limited:
- The system automatically falls back to another available provider.
- A warning is displayed in the UI.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside your venv |
| `ValueError: No API key configured` | Check your `.env` file has the correct key name |
| Blank/empty responses | The model may have returned nothing — try a different model |
| Rate limit errors | Wait a minute, or add keys for other providers |
| PDF extraction fails | Ensure PyPDF2 is installed: `pip install PyPDF2` |

---

## License

MIT — free to use, modify, and distribute.
