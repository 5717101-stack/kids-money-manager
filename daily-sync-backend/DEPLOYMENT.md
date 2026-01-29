# 🚀 פרסום Daily Sync - מדריך מלא

## Tech Stack
- **Backend:** FastAPI (Python) → Render
- **Frontend:** HTML/JS → Vercel
- **Database:** MongoDB Atlas
- **Vector DB:** ChromaDB (local files, או אפשר להעביר ל-cloud)

## שלב 1: הגדרת MongoDB Atlas

### 1.1 יצירת Cluster
1. היכנס ל-[MongoDB Atlas](https://cloud.mongodb.com/)
2. צור cluster חדש (או השתמש בקיים)
3. קבל את ה-Connection String

### 1.2 יצירת Database
- Database name: `daily_sync` (או כל שם שתרצה)
- Collections ייווצרו אוטומטית

### 1.3 Connection String
ה-Connection String ייראה כך:
```
mongodb+srv://username:password@cluster.mongodb.net/daily_sync?retryWrites=true&w=majority
```

## שלב 2: פרסום Backend ב-Render

### 2.1 יצירת חשבון
1. היכנס ל-[Render](https://render.com)
2. הירשם עם GitHub (מומלץ)

### 2.2 יצירת Web Service
1. לחץ **"New +"** → **"Web Service"**
2. בחר **"Build and deploy from a Git repository"**
3. בחר את ה-repository `kids-money-manager`
4. בחר branch: `main` (או `master`)

### 2.3 הגדרת Service

**Name:**
```
daily-sync-backend
```

**Root Directory:**
```
daily-sync-backend
```

**Environment:**
```
Python 3
```

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python main.py
```

**Health Check Path:**
```
/health
```

### 2.4 משתני סביבה

ב-Render Dashboard → Environment Variables, הוסף:

| Key | Value | Notes |
|-----|-------|-------|
| `MONGODB_URI` | `mongodb+srv://...` | Connection string מ-MongoDB Atlas |
| `OPENAI_API_KEY` | `sk-proj-...` | ה-API key שלך |
| `USE_WHISPER_API` | `true` | להשתמש ב-Whisper API |
| `PORT` | (אוטומטי) | Render יקבע אוטומטית |

### 2.5 פרסום
1. לחץ **"Create Web Service"**
2. המתן 3-5 דקות לבנייה
3. קבל את הכתובת (למשל: `daily-sync-backend.onrender.com`)

## שלב 3: פרסום Frontend ב-Vercel

### 3.1 יצירת חשבון
1. היכנס ל-[Vercel](https://vercel.com)
2. הירשם עם GitHub

### 3.2 יצירת Project
1. לחץ **"Add New..."** → **"Project"**
2. בחר את ה-repository `kids-money-manager`
3. בחר **"Import"**

### 3.3 הגדרת Project

**Framework Preset:**
```
Other
```

**Root Directory:**
```
daily-sync-backend/static
```

**Build Command:**
```
(ריק - אין build)
```

**Output Directory:**
```
.
```

### 3.4 משתני סביבה

ב-Vercel Dashboard → Settings → Environment Variables:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://daily-sync-backend.onrender.com` |

### 3.5 עדכון HTML

ערוך את `daily-sync-backend/static/index.html`:

```javascript
const API_BASE = process.env.VITE_API_URL || 'https://daily-sync-backend.onrender.com';
```

### 3.6 פרסום
1. לחץ **"Deploy"**
2. המתן 1-2 דקות
3. קבל את הכתובת (למשל: `daily-sync.vercel.app`)

## שלב 4: עדכון CORS

ב-Render Dashboard → Environment Variables, הוסף:

| Key | Value |
|-----|-------|
| `CORS_ORIGINS` | `https://daily-sync.vercel.app,https://daily-sync-backend.onrender.com` |

ועדכן את `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## שלב 5: בדיקה

### 5.1 בדיקת Backend
```bash
curl https://daily-sync-backend.onrender.com/health
```

צריך להחזיר:
```json
{"status":"healthy","service":"daily-sync-api"}
```

### 5.2 בדיקת Frontend
פתח בדפדפן:
```
https://daily-sync.vercel.app
```

## פתרון בעיות

### Backend לא מתחבר ל-MongoDB
- ודא ש-`MONGODB_URI` נכון
- ודא ש-IP של Render מורשה ב-MongoDB Atlas (Network Access)

### CORS errors
- ודא ש-`CORS_ORIGINS` מוגדר נכון
- ודא שהכתובת של Vercel נכונה

### Health check נכשל
- בדוק את ה-Logs ב-Render
- ודא שהפורט נכון (Render קובע אוטומטית)

## הערות

- **ChromaDB:** נשמר כ-local files ב-Render. אם צריך persistence, שקול להעביר ל-cloud
- **MongoDB:** מומלץ להשתמש ב-MongoDB Atlas (חינמי עד 512MB)
- **Costs:** Render ו-Vercel יש תוכניות חינמיות עם מגבלות

---

**🎉 אחרי הפרסום, האפליקציה תהיה זמינה מכל מקום!**
