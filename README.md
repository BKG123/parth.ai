# Parth.ai 🪶

*Your personal AI guide for goals and growth*

Named after Lord Krishna (Parth - another name for Arjuna's chariot driver), this AI companion guides you toward your goals with wisdom, timely nudges, and unwavering support.

## What It Does

- **Track Goals**: Set and manage multiple goals with intelligent context awareness
- **Proactive Guidance**: Receives timely check-ins and encouragement (not just when you ask)
- **Adaptive Learning**: Understands your patterns, preferences, and what motivates you
- **Smart Memory**: Remembers your progress, struggles, and wins across all goals
- **Skill System**: Reusable goal-tracking patterns that evolve and improve over time

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


## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (for background jobs)
- UV package manager (recommended) or pip

### Setup

1. **Clone and setup environment:**

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

2. **Configure environment:**

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings:
# - TELEGRAM_BOT_TOKEN (get from @BotFather on Telegram)
# - POSTGRES_* (PostgreSQL connection)
# - OPENAI_API_KEY (for AI models)
# - REDIS_HOST (use 'redis' for Docker, 'localhost' for local)
```

3. **Initialize database:**

```bash
# Run migrations
alembic upgrade head
```

4. **Start services:**

```bash
# Terminal 1: Start Redis (if not running)
redis-server

# Terminal 2: Start ARQ worker
source .venv/bin/activate
arq worker.WorkerSettings --watch .

# Terminal 3: Start Telegram bot
source .venv/bin/activate
python main.py
```

Then message your bot on Telegram.

### Docker

```bash
# Start all services (postgres, redis, app, worker)
# Requires TELEGRAM_BOT_TOKEN in .env
docker compose up -d

# With Docker, worker runs automatically - no separate terminal needed
```

### Running Streamlit (optional)

For local development or testing in a browser:

```bash
source .venv/bin/activate
streamlit run app_streamlit.py
```

Then open http://localhost:8501 in your browser.

## Development

### Running the Worker

The background worker handles proactive check-ins using ARQ (runs every 2 hours for users with active goals):

```bash
# Development mode (auto-reload on code changes)
arq worker.WorkerSettings --watch .

# Production mode
arq worker.WorkerSettings
```

### Testing

```bash
# Test reactive agent (conversations)
python tests/test_agents.py reactive "123456789" "How's my progress?"

# Test proactive agent (evaluations)
python tests/test_agents.py proactive 1

# Check system status
python status_check.py
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Project Structure

```
parth.ai/
├── ai/                         # Agent implementations
│   ├── reactive_agent.py       # Conversational agent
│   ├── proactive_agent.py      # Evaluation agent
│   ├── llm_tools.py            # Tool definitions for agents
│   └── agent_manager.py        # Agent coordination
├── models/                     # Database models
│   └── models.py               # SQLAlchemy models
├── prompts/                    # Agent prompts
│   ├── agents.py               # Reactive agent prompt
│   ├── proactive_agent_prompt.py  # Proactive agent prompt
│   └── skills.md               # Skill system documentation
├── services/                   # Business logic
│   └── services.py             # Database operations
├── tasks/                      # Background tasks
│   └── scheduled_messages.py   # Scheduled message execution
├── alembic/                    # Database migrations
├── tests/                      # Test files
├── worker.py                   # ARQ worker configuration
├── app_telegram.py             # Telegram bot (primary interface)
├── app_streamlit.py            # Streamlit web interface (optional)
├── database.py                 # Database connection
├── main.py                     # Main entry point (runs Telegram bot)
```

## Architecture

### Database Schema

**Core Tables:**
- `users` - User accounts (system-managed)
- `user_preferences` - User settings and agent data (agent-managed JSONB)
- `goals` - Goal metadata (system-managed)
- `goal_data` - Goal tracking data (agent-managed JSONB)
- `messages` - Conversation history
- `scheduled_messages` - Proactive messages queue
- `skills` - Reusable goal-tracking patterns
- `goal_skills` - Skill-to-goal mappings

### Agent Autonomy

Parth uses **pure agent autonomy** - the LLM decides everything:

- **Storage structure**: Agent designs data schemas in JSONB fields
- **Messaging timing**: Agent decides when to reach out
- **Skill creation**: Agent creates/reuses/forks goal-tracking patterns
- **Goal tracking**: Agent determines how to track progress

No hardcoded rules - just context-based intelligence.

### Technology Stack

- **Backend**: Python 3.11+, SQLAlchemy, Alembic
- **Database**: PostgreSQL 15+ (JSONB, full-text search)
- **Queue**: Redis + ARQ (async job processing)
- **AI**: OpenAI Agents SDK (Claude Sonnet 4)
- **Interface**: Telegram (primary), Streamlit (optional dev/testing)
- **Deployment**: Docker + docker-compose

## Deployment

### Docker

```bash
# Build and start all services (Telegram bot, worker, postgres, redis)
# Ensure TELEGRAM_BOT_TOKEN is set in .env
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production Checklist

- [ ] Set strong credentials in `.env` (POSTGRES_*, OPENAI_API_KEY)
- [ ] Set `TELEGRAM_BOT_TOKEN` (create bot via @BotFather)
- [ ] Configure `REDIS_HOST` (use `redis` in Docker)
- [ ] Set `OPENAI_API_KEY` for AI models
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Configure monitoring and logging
- [ ] Set up backup strategy for PostgreSQL
- [ ] Configure firewall rules

## Access

### Telegram Bot (primary)
Create a bot via [@BotFather](https://t.me/BotFather), add `TELEGRAM_BOT_TOKEN` to `.env`, and run `python main.py`. Message your bot to start chatting.

### Streamlit (optional)
For browser-based testing: `streamlit run app_streamlit.py` → http://localhost:8501

## Contributing

This is a personal project, but feedback and suggestions are welcome! Please open an issue to discuss any changes.

## License

Private project - all rights reserved.

---

*"Set thy heart upon thy work, but never on its reward"* - Bhagavad Gita