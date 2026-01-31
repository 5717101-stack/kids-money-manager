# 🧠 Second Brain - Daily Sync (Gemini Edition)

אפליקציית ניתוח יומי מתקדמת המשתמשת ב-Google Gemini 1.5 Pro לניתוח מולטימדיה (אודיו, תמונות, טקסט) עם 3 פרספקטיבות מומחים.

## ✨ תכונות

- 🎤 **ניתוח אודיו** - העלה הקלטות יומיות
- 📸 **ניתוח תמונות** - העלה צילומי מסך ותמונות
- 📝 **ניתוח טקסט** - הוסף הערות טקסטואליות
- 🧠 **3 פרספקטיבות מומחים**:
  - **Simon Sinek** - מנהיגות ו-"The Why"
  - **High-Tech Strategy** - יעילות תפעולית ו-KPIs
  - **Adler Institute** - הורות ומשפחה
- 📄 **יצירת PDF** - הורד סיכום מפורט ב-PDF
- 📱 **WhatsApp & SMS** - קבל סיכום בהודעות WhatsApp ו-SMS
- 🌐 **פריסה בענן** - זמין מכל מקום עם פריסה אוטומטית

## 🚀 התחלה מהירה

### התקנה מקומית

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/second-brain-gemini.git
cd second-brain-gemini

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
python -m app.main
```

האפליקציה תהיה זמינה ב-`http://localhost:8001`

## 📋 דרישות

- Python 3.11+
- Google Gemini API Key
- Twilio Account (לשליחת WhatsApp/SMS) - אופציונלי

## 🔧 הגדרת Environment Variables

צור קובץ `.env` עם המשתנים הבאים:

```env
# Google Gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-1.5-pro-latest

# Twilio (אופציונלי)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+972XXXXXXXXX
TWILIO_SMS_FROM=+17692878554
TWILIO_SMS_TO=+972XXXXXXXXX

# Server
PORT=8001
HOST=0.0.0.0
DEBUG=false
```

## 🌐 פריסה בענן

הפרויקט מוכן לפריסה אוטומטית ב-Render.com עם GitHub Actions.

### פריסה מהירה ב-Render:

1. **Fork/Clone** את ה-repository
2. **הירשם ל-[Render.com](https://render.com)** עם GitHub
3. **צור Web Service** חדש:
   - בחר את ה-repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **הוסף Environment Variables** ב-Render Dashboard
5. **שמור** - Render יפרוס אוטומטית!

כל push ל-`main` branch יגרום לפריסה אוטומטית.

📖 **מדריך מפורט**: ראה [DEPLOYMENT_AUTOMATION.md](./DEPLOYMENT_AUTOMATION.md)

## 📚 תיעוד

- [מדריך פריסה אוטומטית](./DEPLOYMENT_AUTOMATION.md)
- [הגדרת Twilio WhatsApp](./TWILIO_WHATSAPP_SETUP.md)
- [הגדרת Twilio Integration](./TWILIO_INTEGRATION_SETUP.md)

## 🏗️ מבנה הפרויקט

```
second-brain-gemini/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── prompts.py           # System prompts for Gemini
│   ├── core/
│   │   └── config.py        # Configuration & settings
│   └── services/
│       ├── gemini_service.py # Gemini API integration
│       ├── pdf_service.py   # PDF generation
│       └── twilio_service.py # WhatsApp/SMS integration
├── static/
│   └── index.html           # Frontend UI
├── .github/
│   └── workflows/          # GitHub Actions workflows
├── requirements.txt         # Python dependencies
├── Procfile                # For Heroku/Railway
├── render.yaml             # Render.com config
└── VERSION                 # Current version
```

## 🔄 ניהול גרסאות

הגרסה נשמרת בקובץ `VERSION` (פורמט: X.Y.Z)

לעדכון גרסה:
```bash
echo "1.7.2" > VERSION
git add VERSION
git commit -m "Bump version to 1.7.2"
git push
```

GitHub Actions יוצר אוטומטית Git tag לכל גרסה חדשה.

## 🧪 בדיקה

```bash
# Test health endpoint
curl http://localhost:8001/health

# Test version endpoint
curl http://localhost:8001/version
```

## 📝 רישיון

MIT License

## 🤝 תרומה

Pull requests מוזמנים! לשאלות, פתח Issue.

## 📞 קשר

לשאלות ותמיכה, פתח Issue ב-GitHub.

---

**גרסה נוכחית:** `1.7.1`

**עודכן לאחרונה:** 2026-01-31
