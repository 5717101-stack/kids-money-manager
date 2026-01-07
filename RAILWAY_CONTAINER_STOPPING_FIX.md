# תיקון: הקונטיינר עוצר לפני שהלוגים נכתבים

## הבעיה
הקונטיינר עוצר לפני שהלוגים נכתבים, מה שאומר ש-Railway לא מזהה את השירות כ-Web Service.

## הפתרון - שלב אחר שלב

### שלב 1: בדוק אם יש Domain מוגדר

1. **לך ל-Railway Dashboard:**
   - Service → Settings → Networking

2. **ודא שיש Domain:**
   - אם אין Domain → לחץ **"Generate Domain"**
   - אם יש Domain → ודא שהוא מוגדר כ-**"Public"** (לא "Private")

3. **הדומיין צריך להיות פעיל:**
   - Status: **"Active"** או **"Public"**
   - אם הוא **"Private"** → שנה אותו ל-**"Public"**

### שלב 2: בדוק את Health Check

1. **ב-Settings, מצא "Health Check":**
   - **Health Check Path:** `/health`
   - **Health Check Enabled:** ✅ (מופעל)
   - **Health Check Timeout:** `600` שניות
   - **Health Check Interval:** `10` שניות

2. **לחץ "Save"**

### שלב 3: בדוק את Root Directory

1. **ב-Settings, מצא "Root Directory":**
   - **Root Directory:** `server`
   - זה אומר ל-Railway שהקוד נמצא בתיקיית `server`

2. **לחץ "Save"**

### שלב 4: בדוק את Start Command

1. **ב-Settings, מצא "Start Command":**
   - **Start Command:** `npm start`
   - **או** השאר ריק - Railway ישתמש ב-Procfile

2. **לחץ "Save"**

### שלב 5: Redeploy

1. **לחץ "Deployments"**
2. **לחץ "..." → "Redeploy"**
3. **המתן 2-3 דקות**

### שלב 6: בדוק את ה-Logs

אחרי ה-Redeploy, בדוק את ה-Logs. אמור לראות:
```
[SERVER] ✅ Health check calls received: X
[SERVER] ✅ Server is running normally
```

אם עדיין רואה:
```
[SERVER] ❌ No health check calls were received!
[SERVER] ⚠️  SIGTERM received
```
→ זה אומר שהשירות עדיין לא מזוהה כ-Web Service.

## איך Railway מזהה Web Service

Railway מזהה אוטומטית שזה Web Service **רק אם**:
1. ✅ יש **Public Domain** מוגדר
2. ✅ יש **Health Check** מוגדר ל-`/health`
3. ✅ השרת עונה על Health Check

**אם אין Domain Public → Railway לא מזהה את זה כ-Web Service → הקונטיינר עוצר!**

## אם עדיין לא עובד

אם אחרי כל זה עדיין הקונטיינר עוצר:

1. **מחק את ה-Service** ב-Railway
2. **צור Service חדש** מההתחלה
3. **הגדר מיד:**
   - Root Directory: `server`
   - Generate Domain (Public)
   - Health Check: `/health`
   - Start Command: `npm start`
4. **Redeploy**

## הערות חשובות

- **Domain = Web Service** - ברגע שיש Domain Public, Railway יודע שזה Web Service
- **ללא Domain Public** → Railway חושב שזה Job → עוצר את הקונטיינר אחרי כמה שניות
- **Health Check חייב להיות מוגדר** ל-`/health`
- אחרי הגדרת Domain, צריך לעשות Redeploy

