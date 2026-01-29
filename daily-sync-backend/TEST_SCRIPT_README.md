# 🧪 Test Script - Daily Sync Simulation

## Overview

`test_script.py` simulates a full day of using the Daily Sync system:
1. Ingests dummy text and audio transcripts
2. Runs all three AI agents on the content
3. Generates a daily digest
4. Shows everything in a readable format

## Quick Start

### Without API Keys (Structure Only)

```bash
cd daily-sync-backend
source venv/bin/activate
python test_script.py
```

This will show:
- ✅ Ingestion process working
- ✅ Content combination
- ✅ Database storage
- ⚠️ Placeholder messages for AI analysis (needs API keys)

### With API Keys (Full AI Analysis)

1. **Add API keys to `.env`**:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   # or
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

2. **Run the script**:
   ```bash
   python test_script.py
   ```

This will show:
- ✅ Full ingestion process
- ✅ Real AI analysis from all 3 personas
- ✅ Generated daily digest with insights
- ✅ Action items and recommendations

## What the Script Does

### Step 1: Ingestion
Simulates ingesting:
- Morning voice note (as text transcript)
- WhatsApp exports (work + family)
- Afternoon reflection
- Evening voice note

### Step 2: Content Combination
Combines all ingested content into a single text for analysis.

### Step 3: AI Agent Analysis
Runs all three agents:
- **Leadership Coach** (Simon Sinek) - analyzes "Why", trust, inspiration
- **Strategy Consultant** - analyzes KPIs, GTM, operational efficiency
- **Parenting Coach** (Adler Institute) - analyzes encouragement, consequences, cooperation

### Step 4: Digest Generation
Synthesizes all agent insights into:
- Executive summary
- Insights by category
- Action items for tomorrow
- Reflection questions

### Step 5: Database Check
Shows what was saved to the database.

## Sample Output

```
================================================================================
                         🧪 Daily Sync - Test Simulation                         
================================================================================

📥 Step 1: Ingesting Daily Content
   ✅ Ingested: 4 items

📋 Step 2: Combining Daily Content
   Combined: 2124 characters

🤖 Step 3: Running AI Agents Analysis
   ✅ Leadership Coach analysis complete
   ✅ Strategy Consultant analysis complete
   ✅ Parenting Coach analysis complete

📝 Step 4: Generating Daily Digest
   ✅ Digest generated

📰 Daily Digest - Final Result
   [Full digest with insights and action items]
```

## Customizing the Test Data

Edit `DUMMY_DAY_DATA` in `test_script.py` to use your own dummy content:

```python
DUMMY_DAY_DATA = {
    "morning_voice_note": "Your custom text here...",
    "whatsapp_export": "Your custom text here...",
    # etc.
}
```

## Troubleshooting

### "OpenAI API key not set"
- Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to `.env`
- Or run without API keys to see the structure

### "Database locked"
- Make sure no other process is using the database
- Close the API server if it's running

### Import errors
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

## Next Steps

After running the test:
1. Check the database: `data/sqlite/daily_sync.db`
2. Use the API: `http://localhost:8000/docs`
3. Modify the dummy data and run again
4. Integrate with real data sources
