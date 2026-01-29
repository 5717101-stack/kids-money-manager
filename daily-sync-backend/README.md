# Daily Sync - AI Life Coach Backend

An AI-powered personal coach backend that ingests daily data (audio, text, images), processes it using specialized LLM personas, and generates actionable daily summaries.

## 🚀 Quick Start

### First Time Setup

1. **Clone the repository** (if working on a different computer):
   ```bash
   git clone <repository-url>
   cd daily-sync-backend
   ```

2. **Create virtual environment and install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # OPENAI_API_KEY=sk-... or ANTHROPIC_API_KEY=sk-ant-...
   ```

4. **Initialize database**:
   ```bash
   python -c "from app.core.database import init_sqlite_db; import asyncio; asyncio.run(init_sqlite_db())"
   ```

5. **Run the server**:
   ```bash
   python main.py
   ```

6. **Access API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📁 Project Structure

```
daily-sync-backend/
├── app/
│   ├── agents/
│   │   └── prompts.py          # System prompts for 3 AI personas
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   ├── database.py         # SQLite & ChromaDB setup
│   │   └── llm.py              # LLM provider utilities
│   ├── routers/
│   │   ├── ingest.py           # Ingestion endpoints
│   │   └── digest.py          # Digest endpoints
│   └── services/
│       ├── ingestion_service.py # Audio/text/image processing
│       ├── agent_service.py     # AI agent orchestration
│       └── digest_service.py    # Daily digest synthesis
├── data/                        # Database storage (gitignored)
├── main.py                      # FastAPI app entry point
├── requirements.txt            # Python dependencies
└── .env.example                # Environment template
```

## 🔑 Features

- **Multi-modal Ingestion**: Support for audio (with Whisper transcription), text, and images
- **Three Expert AI Personas**:
  - **Leadership Coach** (Simon Sinek persona): Focus on "Why", trust, and inspiration
  - **Strategy Consultant**: Data-driven strategic insights for tech and business
  - **Parenting & Home Coach** (Adler Institute persona): Encouragement-based parenting guidance
- **Daily Digest Synthesis**: Combines insights from all three experts into actionable daily summaries
- **Vector Store (RAG)**: ChromaDB for storing and retrieving past insights
- **SQLite Database**: Stores ingestion logs and daily digests

## 📡 API Endpoints

### Ingestion
- `POST /ingest/audio` - Upload and transcribe audio files
- `POST /ingest/text` - Ingest text content
- `POST /ingest/image` - Ingest image files (vision analysis placeholder)

### Daily Digest
- `POST /digest/generate` - Generate daily digest from ingested content
- `GET /digest/{date}` - Retrieve digest for a specific date
- `GET /digest/` - List recent digests

## 🔄 Syncing Between Computers

See [SYNC_INSTRUCTIONS.md](SYNC_INSTRUCTIONS.md) for detailed instructions on working from multiple computers.

## 🛠 Tech Stack

- **Framework**: FastAPI (async)
- **AI**: LangChain with OpenAI (GPT-4o) and Anthropic (Claude 3.5 Sonnet) support
- **Vector DB**: ChromaDB (local)
- **Main DB**: SQLite (async)
- **Transcription**: OpenAI Whisper

## 📝 Environment Variables

See `.env.example` for all available configuration options.

**Required:**
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (at least one)

## 🐛 Troubleshooting

### Database connection errors
- Make sure the `data/` directory exists and is writable
- Run the database initialization command again

### Import errors
- Make sure the virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### API key errors
- Check that `.env` file exists and contains valid API keys
- Verify the keys are correct and have sufficient credits

## 📚 Additional Documentation

- [QUICK_START.md](QUICK_START.md) - Quick start guide
- [SYNC_INSTRUCTIONS.md](SYNC_INSTRUCTIONS.md) - Multi-computer setup
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Setup verification

## 📄 License

MIT
