# בדיקת הגדרות Networking ב-Railway

## מה רואים בתמונה:

✅ **Public Networking:**
- Domain: `web-production-4e378.up.railway.app`
- Port: `3001`
- Status: נראה פעיל

✅ **Private Networking:**
- Domain: `web.railway.internal`
- Status: Ready (יש סימן ✓)

## מה צריך לבדוק:

### 1. ודא שהדומיין Public פעיל:
- בתמונה רואים שיש Public Domain
- **חשוב:** ודא שהדומיין מוגדר כ-**"Public"** (לא "Private")
- אם יש אפשרות לשנות → ודא שזה "Public"

### 2. בדוק את Health Check:
1. לך ל-Settings (לא Networking)
2. מצא "Health Check"
3. ודא:
   - **Health Check Path:** `/health`
   - **Health Check Enabled:** ✅ (מופעל)
   - **Health Check Timeout:** `600` שניות
   - **Health Check Interval:** `10` שניות

### 3. בדוק את Root Directory:
1. ב-Settings, מצא "Root Directory"
2. ודא שזה: `server`

### 4. בדוק את Start Command:
1. ב-Settings, מצא "Start Command"
2. ודא שזה: `npm start` (או ריק - Railway ישתמש ב-Procfile)

## אם הכל תקין אבל הקונטיינר עדיין עוצר:

1. **לחץ "Update"** ליד ה-Domain (אפילו אם לא שינית כלום)
2. **Redeploy** - לחץ "Deployments" → "..." → "Redeploy"
3. **המתן 2-3 דקות**

## איך לזהות שהכל תקין:

אחרי ה-Redeploy, ב-Logs אמור לראות:
```
[SERVER] ✅ Health check calls received: X
[HEALTH] Health check #10 - Server is alive
[HEALTH] Health check #20 - Server is alive
```

אם רואה:
```
[SERVER] ⚠️  SIGTERM received
[SERVER] ❌ No health check calls were received!
```
→ זה אומר שהדומיין לא מזוהה כ-Public או שה-Health Check לא מוגדר נכון.

## הערות:

- **Port 3001** - זה נכון ✅
- **Domain `web-production-4e378.up.railway.app`** - זה נכון ✅
- **Public Networking** - זה נכון ✅

אם הכל מוגדר נכון אבל עדיין יש בעיה, נסה:
1. לחץ "Update" על ה-Domain
2. Redeploy
3. בדוק את ה-Logs

