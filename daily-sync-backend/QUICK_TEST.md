# ⚡ בדיקה מהירה - Daily Sync

## בדיקה מהירה (30 שניות)

```bash
cd daily-sync-backend
source venv/bin/activate

# 1. בדוק שהכל מותקן
python -c "import fastapi, langchain, openai; print('✅ Dependencies OK')"

# 2. בדוק את הקונפיגורציה
python -c "from app.core.config import settings; print(f'✅ Config: {settings.api_title}')"

# 3. אתחל מסד נתונים
python -c "from app.core.database import init_sqlite_db; import asyncio; asyncio.run(init_sqlite_db()); print('✅ DB OK')"

# 4. הרץ את השרת
python main.py
```

## בדיקה עם API

בטרמינל אחר, אחרי שהשרת רץ:

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# Text ingestion test
curl -X POST "http://localhost:8000/ingest/text" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=Test message"
```

## בדיקה בדפדפן

פתח:
- http://localhost:8000/docs - Swagger UI (מומלץ!)
- http://localhost:8000/redoc - ReDoc

## ✅ תוצאות צפויות

אם הכל תקין, תראה:
- ✅ השרת מתחיל בלי שגיאות
- ✅ Health check מחזיר `{"status":"healthy"}`
- ✅ API docs נפתחים בדפדפן
- ✅ Text ingestion מחזיר success

## 🐛 אם יש בעיות

1. **"Module not found"** → `pip install -r requirements.txt`
2. **"Port already in use"** → שנה PORT ב-.env או סגור תהליך אחר
3. **"API key not set"** → זה בסדר אם רק בודקים את המבנה, לא צריך API key לבדיקה בסיסית
