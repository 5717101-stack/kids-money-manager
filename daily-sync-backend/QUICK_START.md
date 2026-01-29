# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add at least one API key:
- `OPENAI_API_KEY=sk-...` (required for OpenAI models)
- `ANTHROPIC_API_KEY=sk-ant-...` (required for Anthropic models)

## 3. Run the Server

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload
```

## 4. Test the API

Visit http://localhost:8000/docs for interactive API documentation.

### Example: Ingest Text

```bash
curl -X POST "http://localhost:8000/ingest/text" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=I had a productive meeting today discussing our Q1 strategy. The team seems energized about the new product direction."
```

### Example: Generate Daily Digest

```bash
curl -X POST "http://localhost:8000/digest/generate?date=2024-01-15"
```

## 5. Project Structure

```
daily-sync-backend/
├── app/
│   ├── agents/
│   │   └── prompts.py          # System prompts for 3 personas
│   ├── core/
│   │   ├── config.py           # Settings
│   │   ├── database.py         # SQLite & ChromaDB
│   │   └── llm.py              # LLM providers
│   ├── routers/
│   │   ├── ingest.py           # /ingest endpoints
│   │   └── digest.py           # /digest endpoints
│   └── services/
│       ├── ingestion_service.py
│       ├── agent_service.py
│       └── digest_service.py
├── data/                        # Database files (gitignored)
├── main.py                      # FastAPI app
└── requirements.txt
```

## Next Steps

1. Ingest some content (text, audio, or images)
2. Generate a daily digest
3. Review the insights from all three AI personas
4. Check the database for stored digests
