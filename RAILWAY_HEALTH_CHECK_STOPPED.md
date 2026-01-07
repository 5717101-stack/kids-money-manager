# תיקון: Health Checks מתחילים ואז נעצרים

## הבעיה
הלוגים מראים:
- ✅ Health check #1 התקבל
- ❌ אחרי 77 שניות, Railway שלח SIGTERM
- ❌ הקונטיינר נעצר

זה אומר ש-Railway קרא ל-health check פעם אחת, אבל אז הפסיק לקרוא.

## הפתרון

### שלב 1: בדוק את Health Check ב-Settings

1. **לך ל-Railway Dashboard:**
   - Service → Settings (לא Networking!)

2. **מצא "Health Check" או "Healthcheck":**
   - **Health Check Path:** `/health` (חייב להיות בדיוק `/health`)
   - **Health Check Enabled:** ✅ (מופעל)
   - **Health Check Timeout:** `600` שניות
   - **Health Check Interval:** `10` שניות (או `30` שניות)

3. **לחץ "Save"**

### שלב 2: ודא שהדומיין Public

1. **לך ל-Networking:**
   - Service → Settings → Networking

2. **ודא שהדומיין מוגדר כ-"Public":**
   - אם יש אפשרות לשנות → ודא שזה "Public" (לא "Private")

3. **לחץ "Update"** (אפילו אם לא שינית כלום)

### שלב 3: בדוק את ה-Response של Health Check

פתח בדפדפן:
```
https://web-production-4e378.up.railway.app/health
```

צריך לראות:
```json
{
  "status": "ok",
  "timestamp": "...",
  "healthCheckCount": X,
  "uptime": X
}
```

אם זה לא עובד → יש בעיה עם ה-Domain.

### שלב 4: Redeploy

1. **לחץ "Deployments"**
2. **לחץ "..." → "Redeploy"**
3. **המתן 2-3 דקות**

### שלב 5: בדוק את ה-Logs

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
→ זה אומר שה-Health Check לא מוגדר נכון ב-Settings.

## הערות חשובות

- **Health Check Path חייב להיות בדיוק `/health`** (לא `/api/health`)
- **Health Check חייב להיות מופעל** ב-Settings
- **הדומיין חייב להיות Public** (לא Private)
- **אחרי שינוי Health Check, צריך Redeploy**

## אם עדיין לא עובד

אם אחרי כל זה עדיין הקונטיינר עוצר:

1. **מחק את ה-Service** ב-Railway
2. **צור Service חדש** מההתחלה
3. **הגדר מיד:**
   - Root Directory: `server`
   - Generate Domain (Public)
   - Health Check Path: `/health` (ב-Settings, לא Networking!)
   - Health Check Enabled: ✅
   - Start Command: `npm start`
4. **Redeploy**

