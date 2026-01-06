# הגדרות Railway - אחרי מחיקת railway.json

## הבעיה
ה-`railway.json` גרם לשגיאת NIXPACKS. מחקנו אותו, עכשיו צריך להגדיר הכל ב-Railway Dashboard.

## הגדרות ב-Railway:

### 1. Root Directory
1. Railway → Service → Settings
2. תחת **"Root Directory"** הזן: `server`
3. לחץ **Save**

### 2. Start Command
1. באותו מקום (Settings)
2. תחת **"Start Command"** הזן: `npm start`
3. לחץ **Save**

### 3. Build Command (אופציונלי)
1. תחת **"Build Command"** השאר ריק או הזן: `npm install`
2. Railway יזהה אוטומטית את package.json

### 4. Environment Variables
1. לחץ **"Variables"** בתפריט
2. ודא שיש:
   - `MONGODB_URI` = (Connection String מ-MongoDB Atlas)
   - `PORT` = `3001`

### 5. Deploy
1. לחץ **"Deployments"**
2. לחץ **"..."** → **"Redeploy"**
3. המתן 2-3 דקות

## מה קרה:
- מחקנו את `railway.json` שגרם לשגיאה
- עכשיו Railway ישתמש בהגדרות מה-Dashboard
- זה יותר פשוט ויציב

## אחרי ה-Deploy:
בדוק את ה-Logs - צריך לראות:
```
Server running on http://0.0.0.0:3001
```

אם עדיין רואה `localhost:3001` → הקוד לא התעדכן. נסה Clear Cache + Redeploy.



