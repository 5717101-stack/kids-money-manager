# 🚀 Deployment Guide - Second Brain Gemini

מדריך מפורט לפריסת הפרויקט בענן עם פריסה אוטומטית מ-GitHub.

## 📋 תוכן עניינים

1. [הכנה לפריסה](#הכנה-לפריסה)
2. [פריסה ב-Render.com](#פריסה-ב-rendercom)
3. [פריסה ב-Railway.app](#פריסה-ב-railwayapp)
4. [פריסה ב-Heroku](#פריסה-ב-heroku)
5. [GitHub Actions - פריסה אוטומטית](#github-actions---פריסה-אוטומטית)
6. [ניהול גרסאות](#ניהול-גרסאות)
7. [פתרון בעיות](#פתרון-בעיות)

---

## הכנה לפריסה

### 1. ודא שהקוד ב-GitHub

```bash
# בדוק שיש לך repository ב-GitHub
git remote -v

# אם לא, צור repository חדש:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/second-brain-gemini.git
git push -u origin main
```

### 2. עדכן את מספר הגרסה

```bash
# ערוך את VERSION
echo "1.7.1" > VERSION
git add VERSION
git commit -m "Bump version to 1.7.1"
git push
```

---

## פריסה ב-Render.com

### יתרונות:
- ✅ חינם (Free tier)
- ✅ פריסה אוטומטית מ-GitHub
- ✅ SSL מובנה
- ✅ קל להגדרה

### שלבים:

1. **הירשם ל-Render**:
   - לך ל-[render.com](https://render.com)
   - הירשם עם GitHub

2. **צור Web Service**:
   - לחץ על "New +" → "Web Service"
   - בחר "Connect GitHub repository"
   - בחר את ה-repository שלך

3. **הגדר את השירות**:
   ```
   Name: second-brain-gemini
   Region: Frankfurt (או קרוב אליך)
   Branch: main
   Root Directory: (השאר ריק)
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

4. **הוסף Environment Variables**:
   - לחץ על "Environment" tab
   - הוסף את כל המשתנים:
     ```
     GOOGLE_API_KEY=your_key
     TWILIO_ACCOUNT_SID=your_sid
     TWILIO_AUTH_TOKEN=your_token
     TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
     TWILIO_WHATSAPP_TO=whatsapp:+972XXXXXXXXX
     TWILIO_SMS_FROM=+17692878554
     TWILIO_SMS_TO=+972XXXXXXXXX
     PORT=8000
     HOST=0.0.0.0
     DEBUG=false
     ```

5. **שמור ופרוס**:
   - לחץ "Create Web Service"
   - Render יתחיל לבנות ולפרוס אוטומטית

6. **קבל את ה-URL**:
   - לאחר הפריסה, תקבל URL כמו: `https://second-brain-gemini.onrender.com`
   - כל push ל-`main` יגרום לפריסה אוטומטית חדשה

---

## פריסה ב-Railway.app

### יתרונות:
- ✅ חינם (Free tier עם $5 credit)
- ✅ פריסה אוטומטית מ-GitHub
- ✅ SSL מובנה
- ✅ קל מאוד להגדרה

### שלבים:

1. **הירשם ל-Railway**:
   - לך ל-[railway.app](https://railway.app)
   - הירשם עם GitHub

2. **צור Project חדש**:
   - לחץ "New Project"
   - בחר "Deploy from GitHub repo"
   - בחר את ה-repository שלך

3. **Railway יזהה אוטומטית**:
   - Railway יזהה את `Procfile` ו-`requirements.txt`
   - הוא יבנה ויפרוס אוטומטית

4. **הוסף Environment Variables**:
   - לחץ על השירות → "Variables" tab
   - הוסף את כל המשתנים (כמו ב-Render)

5. **קבל את ה-URL**:
   - Railway ייצור URL אוטומטית
   - כל push ל-`main` יגרום לפריסה אוטומטית

---

## פריסה ב-Heroku

### יתרונות:
- ✅ יציב ומוכר
- ⚠️ דורש כרטיס אשראי (אבל Free tier זמין)

### שלבים:

1. **התקן Heroku CLI**:
   ```bash
   # macOS
   brew install heroku/brew/heroku
   
   # או הורד מ: https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **התחבר ל-Heroku**:
   ```bash
   heroku login
   ```

3. **צור App**:
   ```bash
   heroku create your-app-name
   ```

4. **הוסף Environment Variables**:
   ```bash
   heroku config:set GOOGLE_API_KEY=your_key
   heroku config:set TWILIO_ACCOUNT_SID=your_sid
   # ... וכו'
   ```

5. **פרוס**:
   ```bash
   git push heroku main
   ```

6. **פתח את האפליקציה**:
   ```bash
   heroku open
   ```

---

## GitHub Actions - פריסה אוטומטית

הפרויקט כולל GitHub Actions workflow לפריסה אוטומטית.

### איך זה עובד:

1. **כל push ל-`main`** → מפעיל את ה-workflow
2. **ה-workflow**:
   - בודק את הקוד
   - מתקין dependencies
   - מפעיל tests (אם יש)
   - מעדכן גרסה
   - מפעיל פריסה (אם מוגדר)

### הגדרת Secrets ב-GitHub:

אם אתה רוצה שהפריסה תתבצע אוטומטית מ-GitHub Actions:

1. **לך ל-GitHub Repository** → Settings → Secrets and variables → Actions
2. **הוסף Secrets** (אופציונלי):
   - `RENDER_SERVICE_ID` - Service ID מ-Render
   - `RENDER_API_KEY` - API Key מ-Render
   - `RAILWAY_TOKEN` - Token מ-Railway
   - `RAILWAY_PROJECT_ID` - Project ID מ-Railway

**הערה**: רוב הספקים (Render, Railway) מטפלים בפריסה אוטומטית ישירות מ-GitHub, אז Secrets לא תמיד נדרשים.

---

## ניהול גרסאות

### איך לעדכן גרסה:

1. **ערוך את `VERSION`**:
   ```bash
   echo "1.7.2" > VERSION
   ```

2. **Commit ו-Push**:
   ```bash
   git add VERSION
   git commit -m "Bump version to 1.7.2"
   git push
   ```

3. **הגרסה תופיע**:
   - בדף ה-web interface
   - ב-`/version` endpoint
   - ב-GitHub Actions logs

### גרסאות אוטומטיות:

אם תרצה, אפשר להוסיף GitHub Action לעדכון אוטומטי של גרסה:

```yaml
# .github/workflows/version-bump.yml
name: Auto Version Bump
on:
  push:
    branches: [main]
jobs:
  bump:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Bump version
        run: |
          # Logic to increment version
```

---

## פתרון בעיות

### הפריסה נכשלת:

1. **בדוק Logs**:
   - Render: Dashboard → Service → Logs
   - Railway: Dashboard → Deployments → View Logs
   - Heroku: `heroku logs --tail`

2. **בדוק Environment Variables**:
   - ודא שכל המשתנים מוגדרים
   - ודא שאין שגיאות כתיב

3. **בדוק Requirements**:
   - ודא ש-`requirements.txt` מעודכן
   - ודא ש-Python version תואם

### האפליקציה לא נגישה:

1. **בדוק את ה-URL**:
   - ודא שה-URL נכון
   - נסה `https://your-app.onrender.com/health`

2. **בדוק Port**:
   - ודא שהאפליקציה מאזינה ל-`$PORT`
   - Render/Railway מגדירים את זה אוטומטית

3. **בדוק CORS**:
   - אם יש בעיות CORS, עדכן את `app/main.py`

### פריסה אוטומטית לא עובדת:

1. **בדוק GitHub Connection**:
   - ודא שה-repository מחובר
   - ודא שיש push ל-`main` branch

2. **בדוק Build Logs**:
   - לך ל-Dashboard של הספק
   - בדוק את ה-Build Logs

---

## סיכום

✅ **הפרויקט מוכן לפריסה!**

1. בחר ספק (Render/Railway מומלצים)
2. חבר את ה-GitHub repository
3. הוסף Environment Variables
4. כל push ל-`main` יגרום לפריסה אוטומטית

**קישורים שימושיים**:
- [Render Dashboard](https://dashboard.render.com)
- [Railway Dashboard](https://railway.app)
- [Heroku Dashboard](https://dashboard.heroku.com)
- [GitHub Actions](https://github.com/YOUR_USERNAME/second-brain-gemini/actions)

---

**שאלות?** פתח Issue ב-GitHub או בדוק את ה-Logs של הספק.
