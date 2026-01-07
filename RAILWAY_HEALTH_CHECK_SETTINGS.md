# הגדרת Health Check ב-Railway - הוראות מפורטות

## ✅ מה עובד:
- Health Check endpoint עובד: `https://web-production-4e378.up.railway.app/health`
- התשובה תקינה: `{"status":"ok",...}`
- Domain מוגדר: `web-production-4e378.up.railway.app`

## ❌ הבעיה:
Railway עדיין עוצר את הקונטיינר אחרי כמה שניות, מה שאומר שה-Health Check לא מוגדר נכון ב-Settings.

## הפתרון - שלב אחר שלב:

### שלב 1: לך ל-Settings (לא Networking!)

1. **ב-Railway Dashboard:**
   - Service → **Settings** (בתפריט השמאלי)
   - **לא** Networking!

### שלב 2: מצא "Health Check"

1. **גלול למטה ב-Settings**
2. **מצא "Health Check" או "Healthcheck" או "Health Check"**
   - זה יכול להיות תחת "Deploy" או "Service Configuration"

### שלב 3: הגדר את Health Check

אם יש אפשרות להגדיר Health Check:

1. **Health Check Path:** `/health` (חייב להיות בדיוק `/health`)
2. **Health Check Enabled:** ✅ (מופעל)
3. **Health Check Timeout:** `600` שניות
4. **Health Check Interval:** `10` שניות (או `30` שניות)

**לחץ "Save"**

### שלב 4: אם אין אפשרות להגדיר Health Check

אם אין אפשרות להגדיר Health Check ב-Settings:

1. **זה אומר ש-Railway מזהה אוטומטית** מה-Procfile
2. **ודא שיש Procfile** עם `web:`
3. **ודא שהדומיין Public**

### שלב 5: ודא שהדומיין Public

1. **לך ל-Networking:**
   - Service → Settings → Networking

2. **לחץ "Update"** ליד ה-Domain
   - אפילו אם לא שינית כלום
   - זה "מרענן" את ההגדרות

3. **ודא שהדומיין מוגדר כ-"Public"**

### שלב 6: Redeploy

1. **לחץ "Deployments"**
2. **לחץ "..." → "Redeploy"**
3. **המתן 2-3 דקות**

### שלב 7: בדוק את ה-Logs

אחרי ה-Redeploy, בדוק את ה-Logs. אמור לראות:
```
[HEALTH] ✅ Health check #1 received
[HEALTH] ✅ Health check #2 received
[HEALTH] ✅ Health check #3 received
...
[HEARTBEAT] Server is alive - health checks: X
```

אם עדיין רואה:
```
[HEALTH] ✅ Health check #1 received
[HEARTBEAT] WARNING: Health checks stopped!
[SERVER] ⚠️  SIGTERM received
```
→ זה אומר שה-Health Check לא מוגדר נכון.

## איפה למצוא Health Check ב-Settings:

Health Check יכול להיות ב:
- **Settings → Deploy → Health Check**
- **Settings → Service Configuration → Health Check**
- **Settings → Health Check** (ישירות)

אם לא מוצאים → זה אומר ש-Railway מזהה אוטומטית מה-Procfile.

## אם עדיין לא עובד:

אם אחרי כל זה עדיין הקונטיינר עוצר:

1. **מחק את ה-Service** ב-Railway
2. **צור Service חדש** מההתחלה
3. **הגדר מיד:**
   - Root Directory: `server`
   - Generate Domain (Public) - מיד!
   - Health Check Path: `/health` (אם יש אפשרות)
   - Start Command: `npm start`
4. **Redeploy**

## הערות חשובות:

- **Health Check Path חייב להיות `/health`** (לא `/api/health`)
- **הדומיין חייב להיות Public** (לא Private)
- **אחרי שינוי Health Check, צריך Redeploy**
- **Procfile חייב להיות עם `web:`** (כבר קיים ✅)

