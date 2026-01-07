# תיקון שגיאת ENV ב-Railway

## הבעיה
```
Build Failed: build daemon returned an error < failed to solve: dockerfile parse error on line 12: ENV names can not be blank >
```

## הפתרון
מחקנו את `nixpacks.toml` ו-`railway.json` שגרמו לשגיאה. עכשיו צריך להגדיר הכל ב-Railway Dashboard.

## הגדרות ב-Railway Dashboard:

### 1. Root Directory
1. Railway → Service → Settings
2. תחת **"Root Directory"** הזן: `server`
3. לחץ **Save**

### 2. Start Command
1. באותו מקום (Settings)
2. תחת **"Start Command"** הזן: `npm start`
   (או השאר ריק - Railway יזהה אוטומטית מה-Procfile)
3. לחץ **Save**

### 3. Build Command
1. תחת **"Build Command"** השאר ריק
   (Railway יזהה אוטומטית את package.json)
2. לחץ **Save**

### 4. Environment Variables
1. לחץ **"Variables"** בתפריט
2. ודא שיש:
   - `MONGODB_URI` = (Connection String מ-MongoDB Atlas)
   - `PORT` = `3001`
   - `RESEND_API_KEY` = (מ-Resend)
   - `RESEND_FROM_EMAIL` = `onboarding@resend.dev` (או domain מותאם)

### 5. Redeploy
1. לחץ **"Deployments"**
2. לחץ **"..."** → **"Redeploy"**
3. המתן 2-3 דקות

## מה קרה:
- מחקנו את `nixpacks.toml` שגרם לשגיאת ENV
- מחקנו את `railway.json` שגרם לבעיות
- עכשיו Railway ישתמש בהגדרות מה-Dashboard + Procfile
- זה יותר פשוט ויציב

## אחרי ה-Deploy:
בדוק את ה-Logs - צריך לראות:
```
Server running on http://0.0.0.0:3001
[RESEND] ✅ Client initialized successfully
```

