# 🚀 פריסה אוטומטית - Second Brain Gemini

מדריך מפורט להגדרת פריסה אוטומטית בענן עם GitHub Actions.

## 📋 תוכן עניינים

1. [הכנה ראשונית](#הכנה-ראשונית)
2. [הגדרת GitHub Repository](#הגדרת-github-repository)
3. [הגדרת Render.com](#הגדרת-rendercom)
4. [GitHub Actions Workflows](#github-actions-workflows)
5. [ניהול גרסאות אוטומטי](#ניהול-גרסאות-אוטומטי)
6. [בדיקת הפריסה](#בדיקת-הפריסה)

---

## הכנה ראשונית

### 1. ודא שהקוד ב-GitHub

```bash
cd second-brain-gemini

# בדוק אם יש repository
git remote -v

# אם לא, צור repository חדש:
git init
git add .
git commit -m "Initial commit - Second Brain Gemini"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/second-brain-gemini.git
git push -u origin main
```

### 2. ודא שכל הקבצים נכונים

```bash
# בדוק שיש:
# - requirements.txt
# - Procfile
# - render.yaml
# - VERSION
# - .github/workflows/*.yml
```

---

## הגדרת GitHub Repository

### 1. צור Repository ב-GitHub

1. לך ל-[GitHub](https://github.com)
2. לחץ "New repository"
3. שם: `second-brain-gemini`
4. בחר "Public" או "Private"
5. **אל תסמן** "Initialize with README" (אם כבר יש לך קוד)
6. לחץ "Create repository"

### 2. Push את הקוד

```bash
git add .
git commit -m "Add deployment automation"
git push origin main
```

### 3. הגדר GitHub Secrets (אופציונלי)

אם תרצה פריסה אוטומטית דרך GitHub Actions:

1. לך ל-Repository → **Settings** → **Secrets and variables** → **Actions**
2. לחץ **New repository secret**
3. הוסף (אם יש לך):
   - `RENDER_API_KEY` - API Key מ-Render
   - `RENDER_SERVICE_ID` - Service ID מ-Render

**הערה**: Render בדרך כלל מטפל בפריסה אוטומטית דרך Webhook, אז Secrets לא תמיד נדרשים.

---

## הגדרת Render.com

### 1. הירשם ל-Render

1. לך ל-[render.com](https://render.com)
2. לחץ "Get Started for Free"
3. הירשם עם GitHub (מומלץ)

### 2. צור Web Service

1. לחץ **"New +"** → **"Web Service"**
2. בחר **"Connect GitHub repository"**
3. בחר את ה-repository `second-brain-gemini`
4. לחץ **"Connect"**

### 3. הגדר את השירות

**Basic Settings:**
```
Name: second-brain-gemini
Region: Frankfurt (או קרוב אליך)
Branch: main
Root Directory: (השאר ריק)
```

**Build & Deploy:**
```
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Plan:**
- בחר **Free** (או Paid אם צריך)

### 4. הוסף Environment Variables

לחץ על **"Environment"** tab והוסף:

```env
# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+972547866168
TWILIO_WHATSAPP_TO=whatsapp:+972505717101
TWILIO_SMS_FROM=+17692878554
TWILIO_SMS_TO=+972505717101

# Server
PORT=8000
HOST=0.0.0.0
DEBUG=false
GEMINI_MODEL=gemini-1.5-pro-latest
```

### 5. שמור ופרוס

1. לחץ **"Create Web Service"**
2. Render יתחיל לבנות ולפרוס אוטומטית
3. תקבל URL כמו: `https://second-brain-gemini.onrender.com`

### 6. הגדר Auto-Deploy

1. לך ל-Service → **Settings** → **Auto-Deploy**
2. ודא ש-**"Auto-Deploy"** מופעל
3. בחר **"main"** branch
4. כל push ל-`main` יגרום לפריסה אוטומטית

---

## GitHub Actions Workflows

הפרויקט כולל 3 workflows:

### 1. `deploy.yml` - פריסה כללית

**מתי רץ:**
- כל push ל-`main` branch
- שינויים ב-`app/`, `static/`, `requirements.txt`, `VERSION`

**מה עושה:**
- ✅ בודק את הקוד
- ✅ מתקין dependencies
- ✅ מריץ syntax checks
- ✅ קורא את מספר הגרסה
- ✅ יוצר Git tag אוטומטית (v1.7.1)
- ✅ מעדכן deployment summary

### 2. `version-check.yml` - בדיקת גרסה

**מתי רץ:**
- שינויים ב-`VERSION` file
- Pull requests שמשנים את `VERSION`

**מה עושה:**
- ✅ בודק שפורמט הגרסה תקין (X.Y.Z)
- ✅ מונע commit של גרסה לא תקינה

### 3. `render-deploy.yml` - פריסה ל-Render

**מתי רץ:**
- Push ל-`main` branch
- Manual trigger (workflow_dispatch)

**מה עושה:**
- ✅ קורא את הגרסה
- ✅ מפעיל פריסה ב-Render (אם מוגדר API key)
- ✅ מעדכן deployment status

---

## ניהול גרסאות אוטומטי

### איך לעדכן גרסה:

1. **ערוך את `VERSION`**:
   ```bash
   echo "1.7.2" > VERSION
   ```

2. **Commit ו-Push**:
   ```bash
   git add VERSION
   git commit -m "Bump version to 1.7.2"
   git push origin main
   ```

3. **מה קורה אוטומטית:**
   - ✅ GitHub Actions בודק את הגרסה
   - ✅ יוצר Git tag (v1.7.2)
   - ✅ מפעיל פריסה ב-Render
   - ✅ הגרסה מופיעה ב-web interface

### גרסאות אוטומטיות (אופציונלי)

אם תרצה, אפשר להוסיף workflow לעדכון אוטומטי:

```yaml
# .github/workflows/auto-version.yml
name: Auto Version Bump
on:
  push:
    branches: [main]
    paths-ignore:
      - 'VERSION'
jobs:
  bump:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Auto bump patch version
        run: |
          # Logic to increment version
```

---

## בדיקת הפריסה

### 1. בדוק GitHub Actions

1. לך ל-Repository → **Actions** tab
2. תראה את כל ה-workflows שרצו
3. לחץ על workflow לראות את הלוגים

### 2. בדוק Render Deployment

1. לך ל-[Render Dashboard](https://dashboard.render.com)
2. לחץ על ה-Service שלך
3. לך ל-**"Events"** tab
4. תראה את כל ה-deployments

### 3. בדוק את האפליקציה

```bash
# בדוק health endpoint
curl https://your-app.onrender.com/health

# בדוק version endpoint
curl https://your-app.onrender.com/version

# פתח בדפדפן
open https://your-app.onrender.com
```

### 4. בדוק Logs

**Render:**
- Dashboard → Service → **Logs** tab

**GitHub Actions:**
- Repository → **Actions** → Click on workflow → **View logs**

---

## פתרון בעיות

### הפריסה לא מתחילה:

1. **בדוק GitHub Connection:**
   - Render Dashboard → Service → **Settings** → **GitHub**
   - ודא שה-repository מחובר

2. **בדוק Branch:**
   - ודא ש-`main` branch נבחר
   - ודא שיש push ל-`main`

3. **בדוק Build Logs:**
   - Render Dashboard → Service → **Logs**
   - חפש שגיאות ב-build

### Environment Variables לא עובדים:

1. **בדוק ב-Render:**
   - Dashboard → Service → **Environment** tab
   - ודא שכל המשתנים מוגדרים

2. **בדוק פורמט:**
   - ודא שאין רווחים מיותרים
   - ודא שאין שגיאות כתיב

### GitHub Actions נכשל:

1. **בדוק Logs:**
   - Repository → **Actions** → Click on failed workflow
   - קרא את ה-error message

2. **בדוק Permissions:**
   - Repository → **Settings** → **Actions** → **General**
   - ודא ש-"Workflow permissions" מוגדר נכון

---

## סיכום

✅ **הפריסה האוטומטית מוכנה!**

**מה קורה עכשיו:**
1. כל push ל-`main` → מפעיל GitHub Actions
2. GitHub Actions → בודק, בונה, ויוצר tag
3. Render → מקבל webhook ומתחיל פריסה
4. האפליקציה → זמינה ב-URL של Render

**קישורים שימושיים:**
- [Render Dashboard](https://dashboard.render.com)
- [GitHub Actions](https://github.com/YOUR_USERNAME/second-brain-gemini/actions)
- [Render Docs](https://render.com/docs)

---

**שאלות?** פתח Issue ב-GitHub או בדוק את ה-Logs.
