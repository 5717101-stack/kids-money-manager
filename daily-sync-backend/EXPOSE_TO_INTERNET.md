# 🌐 חשיפת האפליקציה לאינטרנט

## אופציה 1: ngrok (הכי פשוט - מומלץ להתחלה)

### שלב 1: התקן ngrok

**ב-Mac:**
```bash
brew install ngrok
```

**או הורד ישירות:**
1. לך ל: https://ngrok.com/download
2. הורד את ngrok ל-Mac
3. העתק ל-`/usr/local/bin/`:
   ```bash
   sudo cp ~/Downloads/ngrok /usr/local/bin/
   sudo chmod +x /usr/local/bin/ngrok
   ```

### שלב 2: הירשם ל-ngrok (חינמי)

1. לך ל: https://dashboard.ngrok.com/signup
2. הירשם (חינמי)
3. קבל את ה-auth token מה-Dashboard

### שלב 3: הגדר את ה-token

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### שלב 4: הפעל את השרת

```bash
cd daily-sync-backend
source venv/bin/activate
python main.py
```

### שלב 5: הפעל ngrok בטרמינל נוסף

```bash
ngrok http 8000
```

### שלב 6: קבל את הכתובת

ngrok יציג משהו כמו:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**שמור את הכתובת הזו!** (למשל: `https://abc123.ngrok-free.app`)

### שלב 7: עדכן את ה-HTML

ערוך את `static/index.html` ושינוי את:
```javascript
const API_BASE_URL = "http://localhost:8000";
```

ל:
```javascript
const API_BASE_URL = "https://abc123.ngrok-free.app";  // הכתובת מ-ngrok
```

### הערות:
- ✅ **חינמי** - יש תוכנית חינמית
- ⚠️ **זמני** - הכתובת משתנה בכל הפעלה (אלא אם יש תוכנית בתשלום)
- ✅ **מהיר** - עובד מיד
- ✅ **HTTPS** - אוטומטי

---

## אופציה 2: Railway (פתרון קבוע)

### שלב 1: הירשם ל-Railway

1. לך ל: https://railway.app
2. הירשם עם GitHub

### שלב 2: צור פרויקט חדש

1. לחץ **"New Project"**
2. בחר **"Deploy from GitHub repo"**
3. בחר את ה-repository

### שלב 3: הגדר את ה-Service

**Root Directory:**
```
daily-sync-backend
```

**Start Command:**
```
python main.py
```

**או עם venv:**
```
source venv/bin/activate && python main.py
```

### שלב 4: הוסף משתני סביבה

ב-Railway Dashboard → Variables:
- `OPENAI_API_KEY` = (ה-API key שלך)
- `USE_WHISPER_API` = `true`

### שלב 5: הגדר Domain

1. Settings → Networking
2. לחץ **"Generate Domain"**
3. שמור את הכתובת (למשל: `daily-sync-production.up.railway.app`)

### שלב 6: עדכן את ה-HTML

ערוך את `static/index.html`:
```javascript
const API_BASE_URL = "https://daily-sync-production.up.railway.app";
```

### הערות:
- ✅ **קבוע** - הכתובת לא משתנה
- ✅ **HTTPS** - אוטומטי
- ⚠️ **חינמי מוגבל** - יש מגבלות בתוכנית החינמית
- ✅ **אוטומטי** - מתעדכן אוטומטית מ-GitHub

---

## אופציה 3: Render (חינמי)

### שלב 1: הירשם ל-Render

1. לך ל: https://render.com
2. הירשם עם GitHub

### שלב 2: צור Web Service

1. לחץ **"New +"** → **"Web Service"**
2. בחר את ה-repository
3. הגדר:
   - **Name:** `daily-sync-api`
   - **Root Directory:** `daily-sync-backend`
   - **Start Command:** `python main.py`
   - **Environment:** `Python 3`

### שלב 3: הוסף משתני סביבה

- `OPENAI_API_KEY` = (ה-API key שלך)
- `USE_WHISPER_API` = `true`

### שלב 4: קבל את הכתובת

Render ייצור כתובת כמו: `daily-sync-api.onrender.com`

### שלב 5: עדכן את ה-HTML

```javascript
const API_BASE_URL = "https://daily-sync-api.onrender.com";
```

### הערות:
- ✅ **חינמי** - יש תוכנית חינמית
- ⚠️ **איטי** - יכול להיות איטי אחרי זמן ללא שימוש
- ✅ **קבוע** - הכתובת לא משתנה

---

## אופציה 4: Port Forwarding (אם יש גישה ל-router)

### שלב 1: פתח פורט ב-router

1. היכנס ל-router (למשל: 192.168.1.1)
2. מצא **"Port Forwarding"** או **"Virtual Server"**
3. הוסף כלל:
   - **External Port:** 8000 (או אחר)
   - **Internal IP:** (כתובת ה-IP של המחשב שלך)
   - **Internal Port:** 8000
   - **Protocol:** TCP

### שלב 2: מצא את כתובת ה-IP החיצונית

```bash
curl ifconfig.me
```

### שלב 3: עדכן את ה-HTML

```javascript
const API_BASE_URL = "http://YOUR_EXTERNAL_IP:8000";
```

### הערות:
- ⚠️ **לא מומלץ** - לא מאובטח (HTTP בלבד)
- ⚠️ **מורכב** - דורש גישה ל-router
- ⚠️ **לא יציב** - כתובת ה-IP יכולה להשתנות

---

## המלצה

**להתחלה:** השתמש ב-ngrok - הכי פשוט ומהיר!

**לשימוש קבוע:** השתמש ב-Railway או Render - פתרון קבוע ויציב.

---

## אחרי החשיפה

1. **עדכן את CORS** (אם צריך):
   - ב-`main.py`, עדכן את `allow_origins` ב-CORS middleware

2. **בדוק את האבטחה:**
   - ודא שיש HTTPS (ngrok/Railway/Render מספקים)
   - שקול להוסיף authentication

3. **שמור את הכתובת:**
   - עדכן את `static/index.html` עם הכתובת החדשה
