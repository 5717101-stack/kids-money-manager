# 🔧 הגדרת Environment Variables ב-Render

## ⚠️ חשוב: השרת לא יעבוד בלי המשתנים האלה!

לאחר הפריסה ב-Render, **חובה** להוסיף את המשתנים הבאים:

## 📋 שלבים להוספת Environment Variables

### 1. לך ל-Render Dashboard
- פתח את ה-Service שלך: `second-brain-gemini`
- לחץ על **"Environment"** tab (בצד שמאל)

### 2. הוסף את המשתנים הבאים

לחץ על **"Add Environment Variable"** והוסף כל אחד מהמשתנים הבאים:

#### 🔑 Google Gemini (חובה!)
```
GOOGLE_API_KEY=your_google_api_key_here
```

#### 📱 Twilio (אופציונלי - לשליחת WhatsApp/SMS)
```
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+972XXXXXXXXX
TWILIO_SMS_FROM=+14155238886
TWILIO_SMS_TO=+972XXXXXXXXX
```

#### ⚙️ Server Settings (אופציונלי)
```
PORT=8000
HOST=0.0.0.0
DEBUG=false
GEMINI_MODEL=gemini-2.5-pro
```

### 3. שמור והפעל מחדש

לאחר הוספת כל המשתנים:
1. לחץ **"Save Changes"**
2. Render יתחיל deployment אוטומטי חדש
3. חכה שהפריסה תסתיים (2-3 דקות)

### 4. בדוק שהכל עובד

לאחר הפריסה:
1. לך ל-URL של השירות (לדוגמה: `https://second-brain-gemini.onrender.com`)
2. בדוק את ה-`/health` endpoint
3. נסה להריץ ניתוח דרך הממשק

## 🔍 איך לבדוק אם המשתנים הוגדרו נכון

### דרך Render Dashboard:
1. Service → **Environment** tab
2. תראה רשימה של כל המשתנים שהוגדרו

### דרך Logs:
1. Service → **Logs** tab
2. חפש: `✅ Initialized Gemini model: gemini-2.5-pro`
3. אם אתה רואה: `⚠️ WARNING: GOOGLE_API_KEY not set` - המשתנה לא הוגדר

## ⚠️ שגיאות נפוצות

### "GOOGLE_API_KEY is not configured"
**פתרון:** הוסף את `GOOGLE_API_KEY` ב-Environment Variables

### "The server started successfully, but Gemini analysis requires the API key"
**פתרון:** הוסף את `GOOGLE_API_KEY` ב-Environment Variables

### WhatsApp/SMS לא עובד
**פתרון:** ודא שהוספת את כל משתני Twilio:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `TWILIO_WHATSAPP_TO`
- `TWILIO_SMS_FROM`
- `TWILIO_SMS_TO`

## 📝 הערות חשובות

- **אל תעלה את ה-`.env` ל-GitHub!** - הוא כבר ב-`.gitignore`
- **המשתנים ב-Render הם בטוחים** - הם מוצפנים ולא נגישים לציבור
- **אחרי כל שינוי במשתנים** - Render יפעיל deployment אוטומטי חדש
- **המשתנים נשמרים** - לא צריך להוסיף אותם שוב אחרי deployment

## 🔗 קישורים שימושיים

- [Render Dashboard](https://dashboard.render.com)
- [Render Environment Variables Docs](https://render.com/docs/environment-variables)

---

**💡 טיפ:** שמור את כל המשתנים בקובץ מקומי (לא ב-GitHub!) כדי שתוכל להעתיק אותם בקלות.
