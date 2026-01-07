# תיקון הגדרת Railway: Job → Web Service

## הבעיה
השירות מוגדר כ-"Job" במקום "Web Service", מה שגורם ל-Railway:
- לא לקרוא ל-health check endpoint
- לנסות לעצור את הקונטיינר אחרי כמה שניות
- לא להשאיר את השירות רץ

## הפתרון - שלב אחר שלב

### שלב 1: לך ל-Railway Dashboard
1. היכנס ל-[Railway Dashboard](https://railway.app/dashboard)
2. בחר את הפרויקט שלך
3. לחץ על ה-Service (Backend)

### שלב 2: שנה את Service Type
1. לחץ על **"Settings"** בתפריט
2. גלול למטה למצוא **"Service Type"** או **"Type"**
3. ודא שזה מוגדר כ-**"Web Service"** (לא "Job")
4. אם זה "Job", שנה ל-**"Web Service"**
5. לחץ **"Save"** או **"Update"**

### שלב 3: ודא את ההגדרות הבאות

**Root Directory:**
- צריך להיות: `server`

**Start Command:**
- צריך להיות: `npm start` (או ריק - Railway ישתמש ב-Procfile)

**Health Check Path:**
- צריך להיות: `/health`

**Health Check Timeout:**
- מומלץ: `600` שניות

**Health Check Interval:**
- מומלץ: `10` שניות

### שלב 4: Redeploy
1. לחץ **"Deployments"**
2. לחץ **"..."** → **"Redeploy"**
3. המתן 2-3 דקות

### שלב 5: בדוק את ה-Logs
אחרי ה-Redeploy, בדוק את ה-Logs. אמור לראות:
```
[SERVER] ✅ Health check calls received: X
[SERVER] ✅ Server is running normally
```

אם עדיין רואה:
```
[SERVER] ❌ No health check calls were received!
```
→ זה אומר שהשירות עדיין מוגדר כ-"Job". נסה שוב.

## איך לזהות את הבעיה

**אם השירות מוגדר כ-"Job":**
- Railway לא קורא ל-`/health` endpoint
- הקונטיינר נעצר אחרי כמה שניות
- ה-Logs מציגים: `SIGTERM received`
- ה-Logs מציגים: `No health check calls were received!`

**אם השירות מוגדר כ-"Web Service":**
- Railway קורא ל-`/health` endpoint כל 10 שניות
- הקונטיינר רץ כל הזמן
- ה-Logs מציגים: `Health check calls received: X`

## הערות חשובות

1. **Service Type** הוא ההגדרה החשובה ביותר
2. אם זה "Job", Railway מצפה שהתהליך יסתיים - לא שירות ארוך טווח
3. "Web Service" הוא מה שאנחנו צריכים - שירות שרץ כל הזמן
4. אחרי שינוי ה-Service Type, צריך לעשות Redeploy

## אם עדיין לא עובד

1. ודא שהשירות מוגדר כ-"Web Service" (לא "Job")
2. ודא ש-Root Directory = `server`
3. ודא ש-Start Command = `npm start` (או ריק)
4. ודא ש-Health Check Path = `/health`
5. נסה Clear Cache + Redeploy
