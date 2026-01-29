# ✅ בדיקת פרסום ב-Render

## שלב 1: מצא את הכתובת

1. לך ל-[Render Dashboard](https://dashboard.render.com/)
2. לחץ על ה-service **"daily-sync-backend"**
3. הכתובת תהיה למעלה, למשל:
   ```
   https://daily-sync-backend.onrender.com
   ```
   **שמור את הכתובת הזו!**

## שלב 2: בדוק את Health Endpoint

פתח בדפדפן:
```
https://YOUR_SERVICE_URL.onrender.com/health
```

**צריך להחזיר:**
```json
{"status":"healthy","service":"daily-sync-api"}
```

✅ אם אתה רואה את זה - השרת רץ!

## שלב 3: בדוק את API Docs

פתח בדפדפן:
```
https://YOUR_SERVICE_URL.onrender.com/docs
```

זה יראה לך את כל ה-endpoints הזמינים:
- `/ingest/audio` - העלאת אודיו
- `/ingest/text` - העלאת טקסט
- `/digest/generate` - יצירת daily digest
- `/health` - health check

✅ אם אתה רואה את ה-docs - ה-API עובד!

## שלב 4: בדוק את Web Interface

פתח בדפדפן:
```
https://YOUR_SERVICE_URL.onrender.com/
```

זה אמור להציג את דף ההעלאה עם:
- שדה להעלאת אודיו
- שדה להזנת טקסט
- כפתור "Run AI Analysis"

✅ אם אתה רואה את הדף - הכל עובד!

## שלב 5: בדיקה עם cURL (אופציונלי)

בטרמינל:
```bash
# בדיקת health
curl https://YOUR_SERVICE_URL.onrender.com/health

# בדיקת root
curl https://YOUR_SERVICE_URL.onrender.com/
```

## פתרון בעיות

### Health check נכשל
- בדוק את ה-Logs ב-Render Dashboard
- ודא ש-`MONGODB_URI` מוגדר נכון
- ודא ש-`OPENAI_API_KEY` מוגדר

### 404 Not Found
- ודא ש-Root Directory נכון: `daily-sync-backend`
- ודא ש-Build Command נכון: `pip install -r requirements.txt`
- ודא ש-Start Command נכון: `python main.py`

### 500 Internal Server Error
- בדוק את ה-Logs ב-Render Dashboard
- ודא ש-MongoDB connection string נכון
- ודא שכל ה-dependencies הותקנו

### CORS errors
- ודא ש-`CORS_ORIGINS` מוגדר ב-Environment Variables
- או השאר ריק (אז זה יאפשר הכל)

## ✅ אם הכל עובד

עכשיו תוכל:
1. להעלות קבצי אודיו/טקסט
2. להריץ ניתוח AI
3. לראות את התוצאות

**השלב הבא:** פרסום Frontend ב-Vercel (עקוב אחרי QUICK_DEPLOY.md)

---

**💡 טיפ:** שמור את הכתובת של ה-service - תצטרך אותה לפרסום Frontend!
