# Parth.ai 🪶

*Your personal AI guide for goals and growth*

Named after Lord Krishna (Parth - another name for Arjuna's chariot driver), this AI companion guides you toward your goals with wisdom, timely nudges, and unwavering support.

## What It Does

- **Track Goals**: Set and manage multiple goals with intelligent context awareness
- **Proactive Guidance**: Receives timely check-ins and encouragement (not just when you ask)
- **Adaptive Learning**: Understands your patterns, preferences, and what motivates you
- **Smart Memory**: Remembers your progress, struggles, and wins across all goals

## How It Works

Parth uses a **two-agent architecture** to provide both reactive and proactive support:

### ReactiveAgent 💬
Handles your conversations in real-time. When you message Parth, it responds naturally with full context about your goals, progress, and preferences.

### ProactiveAgent 🧠
Evaluates whether to reach out to you based on your patterns, progress, and timing. Runs every 2 hours to decide if you need encouragement, accountability, or a gentle nudge.

**The Flow:**
1. You set goals and chat naturally with Parth (ReactiveAgent)
2. Every 2 hours, ProactiveAgent evaluates your context
3. It decides: send now, schedule for better time, or skip
4. Messages are sent at optimal times, respecting your preferences

Like Krishna guiding Arjuna, Parth doesn't make decisions for you - it helps you see clearly and stay on course.

📖 **[Full Architecture Documentation](docs/AGENT_ARCHITECTURE.md)**

## Access

### Telegram Bot
Start chatting via Telegram: `@parth_ai_bot` *(coming soon)*

### Web Interface (Testing)
For development and testing, use the Streamlit interface:

```bash
# Quick start
./run_streamlit.sh

# Or manually
source .venv/bin/activate
streamlit run app_streamlit.py
```

Then open http://localhost:8501 in your browser.

## Development

### Running the Worker

The background worker handles proactive check-ins and scheduled messages:

```bash
# Start worker (with auto-reload for development)
arq worker.WorkerSettings --watch .

# Production
arq worker.WorkerSettings
```

### Testing Agents

```bash
# Test reactive agent (conversations)
python test_agents.py reactive "123456789" "How's my progress?"

# Test proactive agent (evaluations)
python test_agents.py proactive 1
```

### Project Structure

```
parth.ai/
├── ai/
│   ├── reactive_agent.py      # Conversational agent
│   ├── proactive_agent.py     # Evaluation agent
│   └── llm_tools.py            # Tool definitions
├── prompts/
│   ├── agents.py               # Reactive prompt
│   └── proactive_agent_prompt.py  # Proactive prompt
├── tasks/
│   └── scheduled_messages.py   # Execute scheduled messages
├── worker.py                   # ARQ worker with cron jobs
└── docs/
    ├── AGENT_ARCHITECTURE.md   # Full architecture docs
    └── IMPLEMENTATION_SUMMARY.md  # Implementation details
```

---

*"Set thy heart upon thy work, but never on its reward"* - Bhagavad Gita