# 🚀 פרסום ב-Render - שלב אחר שלב

## מה אתה רואה עכשיו?

זה Render Dashboard - פרויקט "DailyAI" (או Daily Sync).
הסביבה "Production" ריקה - צריך ליצור service חדש.

## שלב 1: לחץ על "+ Create new service"

במסך שאתה רואה, לחץ על הכפתור הכחול/סגול:
**"+ Create new service"**

## שלב 2: בחר "Web Service"

תראה רשימה של אפשרויות:
- **Web Service** ← בחר את זה!
- Background Worker
- Cron Job
- PostgreSQL
- Redis
- וכו'

## שלב 3: בחר "Build and deploy from a Git repository"

תראה 3 אפשרויות:
1. **Build and deploy from a Git repository** ← בחר את זה!
2. Deploy an existing image
3. Run a Dockerfile

## שלב 4: בחר את ה-Repository

אם זה לא מחובר:
1. לחץ "Connect account" (GitHub/GitLab/Bitbucket)
2. אשר את הגישה
3. בחר את ה-repository: **kids-money-manager**

אם כבר מחובר:
- בחר את **kids-money-manager** מהרשימה

## שלב 5: הגדר את ה-Service

### Name:
```
daily-sync-backend
```

### Branch:
```
main
```
(או `master` - תלוי ב-GitHub שלך)

### Root Directory:
```
daily-sync-backend
```
**חשוב מאוד!** זה אומר ל-Render שהקוד נמצא בתיקייה הזו.

### Environment:
```
Python 3
```

### Build Command:
```
pip install -r requirements.txt
```

### Start Command:
```
python main.py
```

### Health Check Path:
```
/health
```

## שלב 6: הוסף Environment Variables

גלול למטה למצוא **"Environment Variables"** ולחץ **"Add Environment Variable"**

הוסף את המשתנים הבאים:

| Key | Value | איפה למצוא |
|-----|-------|------------|
| `MONGODB_URI` | `mongodb+srv://BacharIsraeli:YOUR_PASSWORD@bacharisraeli.xgmevpl.mongodb.net/daily_sync?appName=BacharIsraeli&retryWrites=true&w=majority` | מה-.env שלך (החלף YOUR_PASSWORD) |
| `OPENAI_API_KEY` | `sk-proj-YOUR_API_KEY_HERE` | מה-.env שלך |
| `USE_WHISPER_API` | `true` | - |

**הערה:** `PORT` ייקבע אוטומטית על ידי Render - לא צריך להוסיף אותו.

## שלב 7: פרסום

1. גלול למטה
2. לחץ **"Create Web Service"**
3. המתן 3-5 דקות לבנייה

## שלב 8: קבל את הכתובת

אחרי שהבנייה מסתיימת, Render ייצור כתובת כמו:
```
daily-sync-backend.onrender.com
```

**שמור את הכתובת הזו!** תצטרך אותה לפרסום Frontend ב-Vercel.

## בדיקה

פתח בדפדפן:
```
https://daily-sync-backend.onrender.com/health
```

צריך להחזיר:
```json
{"status":"healthy","service":"daily-sync-api"}
```

## ✅ סיימת!

עכשיו ה-Backend רץ ב-Render!

**השלב הבא:** פרסום Frontend ב-Vercel (עקוב אחרי QUICK_DEPLOY.md)

---

**💡 טיפ:** אם יש שגיאות ב-Logs, בדוק:
- האם Root Directory נכון? (`daily-sync-backend`)
- האם Build Command נכון? (`pip install -r requirements.txt`)
- האם Start Command נכון? (`python main.py`)
- האם Environment Variables מוגדרים נכון?
