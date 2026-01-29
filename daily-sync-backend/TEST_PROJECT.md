# 🧪 בדיקת הפרויקט

## בדיקה מהירה (אוטומטית)

הרץ את הסקריפט:
```bash
cd daily-sync-backend
source venv/bin/activate
./test_api.sh
```

## בדיקה ידנית - שלב אחר שלב

### 1. בדיקת סביבה וירטואלית
```bash
cd daily-sync-backend
source venv/bin/activate
python --version  # צריך להיות Python 3.9+
```

### 2. בדיקת תלויות
```bash
python -c "import fastapi, uvicorn, langchain, openai, anthropic, chromadb, aiosqlite; print('✅ OK')"
```

### 3. בדיקת קונפיגורציה
```bash
python -c "from app.core.config import settings; print(settings.api_title)"
```

### 4. בדיקת Prompts
```bash
python -c "from app.agents.prompts import get_all_prompts; print(len(get_all_prompts()))"
```

### 5. בדיקת מסד נתונים
```bash
python -c "from app.core.database import init_sqlite_db; import asyncio; asyncio.run(init_sqlite_db())"
```

### 6. הרצת השרת
```bash
python main.py
```

השרת צריך להתחיל ולהציג:
```
🚀 Starting Daily Sync API...
✅ Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7. בדיקת API (בטרמינל אחר)

#### בדיקת Health Check:
```bash
curl http://localhost:8000/health
```

צריך להחזיר:
```json
{"status":"healthy","service":"daily-sync-api"}
```

#### בדיקת Root:
```bash
curl http://localhost:8000/
```

#### בדיקת Text Ingestion:
```bash
curl -X POST "http://localhost:8000/ingest/text" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=This is a test message"
```

#### בדיקת API Documentation:
פתח בדפדפן:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## בדיקות מתקדמות

### בדיקה עם API Key (אם יש לך)

אם יש לך OpenAI API key, תוכל לבדוק את ה-Agents:

```bash
# הוסף טקסט
curl -X POST "http://localhost:8000/ingest/text" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=I had a productive meeting today discussing our Q1 strategy."

# צור digest (צריך API key ב-.env)
curl -X POST "http://localhost:8000/digest/generate"
```

## פתרון בעיות

### שגיאת "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### שגיאת "Database locked"
```bash
# סגור את השרת ונסה שוב
# או מחק את data/sqlite/daily_sync.db וצור מחדש
```

### שגיאת "API key not set"
```bash
# וודא שיש קובץ .env עם API key
cp .env.example .env
# ערוך .env והוסף את ה-API key שלך
```

### השרת לא מתחיל
```bash
# בדוק שהפורט 8000 פנוי
lsof -i :8000
# או שנה את הפורט ב-.env
```

## ✅ Checklist

- [ ] סביבה וירטואלית פעילה
- [ ] כל התלויות מותקנות
- [ ] קובץ .env קיים (אם צריך API keys)
- [ ] מסד נתונים מאותחל
- [ ] השרת מתחיל בהצלחה
- [ ] Health check מחזיר OK
- [ ] API docs נפתחים בדפדפן
- [ ] Text ingestion עובד

## 🎯 מה הלאה?

אחרי שהכל עובד:
1. הוסף API keys ל-.env
2. נסה להעלות טקסט/אודיו
3. צור daily digest
4. בדוק את התוצאות
