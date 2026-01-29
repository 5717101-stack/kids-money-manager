# 🚀 פרסום מהיר - Daily Sync

## שלב 1: הגדרת MongoDB (אם עדיין לא)

אם יש לך כבר MongoDB Atlas (מאפליקציית ניהול תקציב הילדים):
1. השתמש באותו connection string
2. רק שנה את שם ה-database ל-`daily_sync` (או כל שם שתרצה)

אם אין:
1. לך ל-[MongoDB Atlas](https://cloud.mongodb.com/)
2. צור cluster חינמי
3. קבל את ה-Connection String

## שלב 2: הגדרת .env

צור קובץ `.env` ב-`daily-sync-backend/`:

```bash
cd daily-sync-backend
cp .env.example .env
```

ערוך את `.env` והוסף:
```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/daily_sync?retryWrites=true&w=majority
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```

## שלב 3: פרסום Backend ב-Render

### 3.1 יצירת Service
1. לך ל-[Render Dashboard](https://dashboard.render.com/)
2. לחץ **"New +"** → **"Web Service"**
3. בחר **"Build and deploy from a Git repository"**
4. בחר את ה-repository `kids-money-manager`
5. בחר branch: `main`

### 3.2 הגדרות
- **Name:** `daily-sync-backend`
- **Root Directory:** `daily-sync-backend`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`
- **Health Check Path:** `/health`

### 3.3 משתני סביבה
הוסף ב-Render Dashboard → Environment Variables:

| Key | Value |
|-----|-------|
| `MONGODB_URI` | (מה-.env שלך) |
| `OPENAI_API_KEY` | (מה-.env שלך) |
| `USE_WHISPER_API` | `true` |
| `PORT` | (אוטומטי - Render יקבע) |

### 3.4 פרסום
1. לחץ **"Create Web Service"**
2. המתן 3-5 דקות
3. שמור את הכתובת (למשל: `daily-sync-backend.onrender.com`)

## שלב 4: פרסום Frontend ב-Vercel

### 4.1 יצירת Project
1. לך ל-[Vercel Dashboard](https://vercel.com/dashboard)
2. לחץ **"Add New..."** → **"Project"**
3. בחר את ה-repository `kids-money-manager`
4. לחץ **"Import"**

### 4.2 הגדרות
- **Framework Preset:** `Other`
- **Root Directory:** `daily-sync-backend/static`
- **Build Command:** (ריק)
- **Output Directory:** `.`

### 4.3 משתני סביבה
הוסף ב-Vercel Dashboard → Settings → Environment Variables:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://daily-sync-backend.onrender.com` |

(החלף בכתובת ה-Render שלך)

### 4.4 עדכון HTML
ערוך את `daily-sync-backend/static/index.html`:
- מצא את השורה עם `API_BASE`
- ודא שהיא משתמשת ב-`process?.env?.VITE_API_URL`

### 4.5 פרסום
1. לחץ **"Deploy"**
2. המתן 1-2 דקות
3. שמור את הכתובת (למשל: `daily-sync.vercel.app`)

## שלב 5: עדכון CORS

ב-Render Dashboard → Environment Variables, הוסף:

| Key | Value |
|-----|-------|
| `CORS_ORIGINS` | `https://daily-sync.vercel.app` |

(החלף בכתובת ה-Vercel שלך)

## שלב 6: בדיקה

### בדיקת Backend:
```bash
curl https://daily-sync-backend.onrender.com/health
```

צריך להחזיר:
```json
{"status":"healthy","service":"daily-sync-api"}
```

### בדיקת Frontend:
פתח בדפדפן:
```
https://daily-sync.vercel.app
```

## ✅ סיימת!

האפליקציה זמינה מכל מקום:
- Frontend: `https://daily-sync.vercel.app`
- Backend: `https://daily-sync-backend.onrender.com`

---

**💡 טיפ:** אם משהו לא עובד, בדוק את ה-Logs ב-Render Dashboard.
