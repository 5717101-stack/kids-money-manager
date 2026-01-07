# הגדרת Railway - מדריך סופי

## תשובה קצרה
**לא צריך להגדיר את הדומיין בקוד!** הדומיין מוגדר ב-Railway Dashboard בלבד.

## מה צריך לעשות

### 1. ב-Railway Dashboard (לא בקוד!)

1. **לך ל-Service → Settings → Networking:**
   - לחץ **"Generate Domain"** או **"Add Domain"**
   - Railway ייצור domain אוטומטית
   - **חשוב:** ודא שהדומיין מוגדר כ-**"Public"** (לא "Private")

2. **הדומיין ייראה כך:**
   ```
   web-production-4e378.up.railway.app
   ```

### 2. בקוד - רק עדכון כתובת ה-API

הקוד כבר מעודכן להשתמש בכתובת:
```javascript
const PRODUCTION_API = 'https://web-production-4e378.up.railway.app/api';
```

**זה הכל!** אין צורך להגדיר את הדומיין בקוד.

### 3. מה הקוד צריך

הקוד צריך רק:
- ✅ **Procfile** - `web: cd server && npm start` (כבר קיים)
- ✅ **Health Check endpoint** - `/health` (כבר קיים)
- ✅ **Start Command** - `npm start` (כבר קיים)

**אין צורך בקובץ config נוסף!**

## סיכום - מה צריך להגדיר

### ב-Railway Dashboard:
1. ✅ **Networking → Generate Domain** → Public
2. ✅ **Settings → Root Directory** → `server`
3. ✅ **Settings → Start Command** → `npm start` (או ריק)
4. ✅ **Settings → Health Check** → `/health`
5. ✅ **Variables** → `MONGODB_URI`, `RESEND_API_KEY`, וכו'

### בקוד:
- ✅ **Procfile** - כבר קיים
- ✅ **Health Check** - כבר קיים ב-`/health`
- ✅ **Start Command** - כבר קיים ב-`package.json`

**אין צורך להגדיר דומיין בקוד!**

## איך Railway מזהה Web Service

Railway מזהה אוטומטית שזה Web Service אם:
1. ✅ יש **Procfile** עם `web:`
2. ✅ יש **Public Domain** מוגדר ב-Dashboard
3. ✅ יש **Health Check** endpoint (`/health`)
4. ✅ השרת עונה על Health Check

**הכל כבר מוגדר בקוד!** רק צריך להגדיר את הדומיין ב-Dashboard.

