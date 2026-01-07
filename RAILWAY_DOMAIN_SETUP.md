# הגדרת Domain ב-Railway - Web Service

## הבעיה
Railway לא מזהה את השירות כ-Web Service כי אין Domain/Public URL מוגדר.

## הפתרון - שלב אחר שלב

### שלב 1: הגדרת Domain ב-Railway Dashboard

1. **לך ל-Railway Dashboard:**
   - היכנס ל-[Railway Dashboard](https://railway.app/dashboard)
   - בחר את הפרויקט שלך
   - לחץ על ה-Service (Backend)

2. **לך ל-Settings:**
   - לחץ על **"Settings"** בתפריט
   - גלול למטה למצוא **"Networking"** או **"Domains"**

3. **הגדר Public Domain:**
   - לחץ על **"Generate Domain"** או **"Add Domain"**
   - Railway ייצור domain אוטומטית (למשל: `web-production-4e378.up.railway.app`)
   - **או** אם כבר יש domain, ודא שהוא מוגדר כ-**"Public"**

4. **ודא שהדומיין פעיל:**
   - ה-Domain צריך להיות **"Active"** או **"Public"**
   - אם הוא **"Private"**, שנה אותו ל-**"Public"**

### שלב 2: הגדרת Health Check

1. **ב-Settings, מצא "Health Check":**
   - **Health Check Path:** `/health`
   - **Health Check Timeout:** `600` שניות
   - **Health Check Interval:** `10` שניות
   - **Health Check Enabled:** ✅ (מופעל)

2. **לחץ "Save"**

### שלב 3: הגדרת Root Directory

1. **ב-Settings, מצא "Root Directory":**
   - **Root Directory:** `server`
   - זה אומר ל-Railway שהקוד נמצא בתיקיית `server`

2. **לחץ "Save"**

### שלב 4: הגדרת Start Command

1. **ב-Settings, מצא "Start Command":**
   - **Start Command:** `npm start`
   - **או** השאר ריק - Railway ישתמש ב-Procfile

2. **לחץ "Save"**

### שלב 5: ודא את משתני הסביבה

1. **לחץ "Variables" בתפריט:**
   - ודא שיש:
     - `MONGODB_URI` = (Connection String)
     - `PORT` = `3001` (אופציונלי - Railway יקבע אוטומטית)
     - `RESEND_API_KEY` = (מ-Resend)
     - `RESEND_FROM_EMAIL` = `onboarding@resend.dev`

### שלב 6: Redeploy

1. **לחץ "Deployments"**
2. **לחץ "..." → "Redeploy"**
3. **המתן 2-3 דקות**

### שלב 7: בדוק את ה-Logs

אחרי ה-Redeploy, בדוק את ה-Logs. אמור לראות:
```
[SERVER] ✅ Health check calls received: X
[SERVER] ✅ Server is running normally
```

אם עדיין רואה:
```
[SERVER] ❌ No health check calls were received!
```
→ בדוק ש:
1. יש Domain מוגדר כ-"Public"
2. Health Check מוגדר ל-`/health`
3. Health Check מופעל

## איך Railway מזהה Web Service

Railway מזהה אוטומטית שזה Web Service אם:
1. ✅ יש **Public Domain** מוגדר
2. ✅ יש **Health Check** מוגדר
3. ✅ יש **Start Command** או **Procfile**
4. ✅ השרת עונה על ה-Health Check

## אם אין אפשרות ליצור Domain

אם Railway לא נותן לך ליצור Domain (בגלל תוכנית חינמית):
1. בדוק אם יש **"Networking"** או **"Public URL"** ב-Settings
2. ודא ש-Health Check מוגדר נכון
3. נסה ליצור Service חדש ולהגדיר אותו מההתחלה

## הערות חשובות

- **Domain = Web Service** - ברגע שיש Domain, Railway יודע שזה Web Service
- **Health Check** חייב להיות מוגדר ל-`/health`
- **Root Directory** חייב להיות `server`
- אחרי הגדרת Domain, צריך לעשות Redeploy

