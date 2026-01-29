# 🔧 תיקון: Render מזהה Node.js במקום Python

## הבעיה

Render עדיין מזהה Node.js במקום Python, למרות שהגדרנו Python 3.

**סימנים:**
- Logs מראים: `Requesting Node.js version 22`
- Build נכשל עם `keyerror: __version__`
- Render לא מוצא את `requirements.txt`

## הסיבה

**Root Directory לא מוגדר נכון ב-Render Dashboard!**

Render מחפש ב-root של ה-repo (איפה שיש `.nvmrc`), ולא ב-`daily-sync-backend/`.

## פתרון

### שלב 1: בדוק את ההגדרות ב-Render

1. לך ל-[Render Dashboard](https://dashboard.render.com/)
2. לחץ על ה-service **"daily-sync-backend"**
3. לחץ על **"Settings"** (בסיידבר)

### שלב 2: ודא את ההגדרות הבאות

**Root Directory:**
```
daily-sync-backend
```
⚠️ **זה החשוב ביותר!** זה חייב להיות בדיוק `daily-sync-backend` (לא `./daily-sync-backend` או `/daily-sync-backend`)

**Environment:**
```
Python 3
```
⚠️ **לא Node.js!** אם אתה רואה "Node" או "Node.js", שנה ל-"Python 3"

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python main.py
```

### שלב 3: Clear Build Cache

1. ב-Settings, גלול למטה
2. לחץ על **"Clear Build Cache"**
3. אשר את הפעולה

### שלב 4: Manual Deploy

1. לך ל-**"Events"** או **"Manual Deploy"**
2. לחץ על **"Manual Deploy"** → **"Deploy latest commit"**
3. המתן 5-10 דקות

### שלב 5: בדוק את ה-Logs

אחרי ה-Deploy, בדוק את ה-Logs. אתה צריך לראות:
- ✅ `Using Python version...` (לא Node.js!)
- ✅ `Installing dependencies from requirements.txt`
- ✅ `Starting server...`

אם אתה עדיין רואה `Requesting Node.js version...`, זה אומר ש-Root Directory עדיין לא נכון.

## אם עדיין לא עובד

### אפשרות 1: מחק ויצור מחדש

1. מחק את ה-service `daily-sync-backend`
2. צור service חדש
3. הפעם ודא ש-Root Directory = `daily-sync-backend` מההתחלה

### אפשרות 2: בדוק את render.yaml

אם אתה משתמש ב-`render.yaml`, ודא שהוא ב-root של ה-repo (לא ב-`daily-sync-backend/`):

```yaml
services:
  - type: web
    name: daily-sync-backend
    env: python
    rootDir: daily-sync-backend  # ← זה חשוב!
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
```

אבל **Render לא קורא render.yaml מתוך תיקייה משנית!** הוא קורא רק מ-root.

## בדיקה מהירה

אחרי התיקון, בדוק:
1. Health endpoint: `https://daily-sync-backend.onrender.com/health`
2. API docs: `https://daily-sync-backend.onrender.com/docs`

---

**💡 טיפ:** אם אתה לא בטוח מה ה-Root Directory, בדוק את ה-Logs - אם אתה רואה `Requesting Node.js`, זה אומר ש-Root Directory לא נכון.
