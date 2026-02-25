# Scoutly — Universal AI Scouting Agent

An autonomous, domain-agnostic intelligence system that uses LLM-driven browser automation to scout, extract, and summarize information from the web, delivered to users via a LINE Messaging Bot with a two-phase interactive UI.

> Built as a side project to explore **Agentic Workflow**, **async backend architecture**, and **real-world LLM integration** on a production-deployed service.

---

## 🏗 System Architecture

```
User (LINE) ──► FastAPI Webhook ──► Background Task (asyncio)
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
                   ConfigLoader                       ScoutAgent
                 (YAML Registry)              (browser-use + GPT-4o)
                         │                                 │
                  Domain Config                   Phase 1: Discovery
               (sources, goals,                  Phase 2: Deep Dive
                focus_points)                            │
                                                         ▼
                                               LINE Flex Message UI
                                              (UiGenerator → Postback)
```

The system is split into four decoupled layers:

| Layer | File | Responsibility |
|---|---|---|
| Config | `domain_configs/*.yaml` | Defines scouting sources, goals, and focus points per domain |
| Logic | `scout_agent.py` | Orchestrates browser-based agent with dynamic prompt injection |
| Transport | `app.py` | FastAPI webhook + async background task scheduling |
| Interface | `ui_generator.py` | Converts structured JSON output into LINE Flex Message cards |

---

## 🔑 Key Engineering Decisions

### 1. LLM-Driven Browser Automation over Traditional Scraping
Traditional scrapers (`requests` + `BeautifulSoup`) break when sites use JavaScript rendering, anti-bot detection, or change their DOM structure. This project uses [`browser-use`](https://github.com/browser-use/browser-use), which lets GPT-4o control a real Chromium browser — navigating, clicking, and extracting content exactly as a human would. This eliminates fragile CSS selectors entirely.

### 2. Domain-Agnostic Design via YAML Registry
Each domain (AIOps, Stocks, etc.) is fully described in a YAML config file. `ScoutAgent` injects these values dynamically into the LLM's task prompt at runtime — meaning **zero code changes** are needed to onboard a new domain. Adding `beauty.yaml` instantly gives the bot a beauty reporter.

```yaml
# domain_configs/aiops.yaml
scouting_logic:
  discovery_goal: "Identify articles related to AIOps, LLM observability, or GPU resource scheduling."
  focus_points:
    - "Core technical architecture"
    - "Impact on DevOps workflows"
```

### 3. Async Webhook + Background Task to Handle Long-Running Agents
LINE's webhook has a strict response timeout (~5s). Since `browser-use` agents take 30–60 seconds to complete, a naive synchronous approach would always time out. The solution:

1. Webhook handler replies immediately (`reply_message`) to satisfy LINE's timeout.
2. The actual agent execution is offloaded with `asyncio.create_task()`.
3. Once complete, the result is pushed to the user via `push_message`.

This pattern decouples user-perceived latency from actual processing time.

### 4. Two-Phase Interactive UI (Discovery → Deep Dive)
Instead of dumping a wall of text, the bot presents a **Flex Message card** listing article titles. Each card has a **Postback button** that triggers `run_summary()` — a second agent pass that reads the full article and returns a structured analysis. The URL is passed statlessly through the postback `data` field, avoiding the need for a session store.

### 5. LLM Proxy Pattern to Resolve Dependency Incompatibility
`browser-use` internally validates that the LLM object has a `provider` field, which `langchain-openai`'s `ChatOpenAI` does not expose as a Pydantic field in its current version. Subclassing caused `ainvoke` to be lost from the Pydantic model. The fix was a lightweight **Proxy pattern**:

```python
class LLMProxy:
    def __init__(self, llm):
        self.llm = llm
        self.provider = "openai"       # satisfies browser-use's check
    def __getattr__(self, name):
        return getattr(self.llm, name) # delegates everything else to the real LLM
```

This preserves all async methods while injecting the missing attribute — without touching the underlying object's Pydantic schema.

---

## 🛠 Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.11 |
| AI Agent | [browser-use](https://github.com/browser-use/browser-use) + Playwright (Chromium) |
| LLM | OpenAI GPT-4o via `langchain-openai` |
| Backend | FastAPI + Uvicorn (async) |
| Messaging | LINE Messaging API SDK v3 |
| Deployment | Render (PaaS) |
| Config | PyYAML |

---

## 📂 Project Structure

```
Scoutly/
├── app.py              # FastAPI webhook server, async task orchestration
├── scout_agent.py      # Core AI agent: discovery + deep-dive summary
├── ui_generator.py     # LINE Flex Message builder
├── config_loader.py    # YAML domain registry loader
├── domain_configs/
│   ├── aiops.yaml      # AIOps / LLM observability domain
│   └── stocks.yaml     # Taiwan semiconductor news domain
├── requirements.txt
└── Procfile            # Render deployment entry point
```