# הגדרת שירות חדש ב-Railway

## הבעיה
השירות החדש מחפש את הקובץ ב-`/app/server.js` אבל הוא לא שם.

## הפתרון
צריך להגדיר את Root Directory ל-`server` בשירות החדש.

## שלבים

### 1. הגדרת Root Directory
1. היכנס ל-Railway Dashboard
2. בחר את השירות החדש שיצרת
3. לחץ על **Settings**
4. תחת **General** או **Service Configuration**, מצא:
   - **Root Directory**
   - **Working Directory**
   - **Source Directory**
5. שנה אותו ל: `server`
6. שמור

### 2. הגדרת Start Command
1. תחת **Settings → Deploy** או **Settings → Start Command**
2. ודא ש-Start Command הוא: `node server.js`
3. (או השאר את זה ריק אם יש Procfile)

### 3. הגדרת Health Check
1. תחת **Settings → Health Check**
2. ודא ש:
   - **Health Check Path**: `/health`
   - **Health Check Timeout**: 600 שניות
   - **Health Check Interval**: 10 שניות

### 4. Redeploy
1. לחץ על **Deployments**
2. לחץ על **Redeploy** או המתן ל-auto deploy
3. השרת אמור להתחיל בהצלחה

## אם עדיין לא עובד

אם עדיין מקבלים `Cannot find module '/app/server.js'`:

### אפשרות 1: שנה את Start Command
1. Settings → Start Command
2. שנה ל: `cd server && node server.js`
3. Redeploy

### אפשרות 2: שנה את Procfile
אם יש Procfile, שנה אותו ל:
```
web: cd server && node server.js
```

### אפשרות 3: בדוק את המבנה
ודא שהמבנה של הפרויקט הוא:
```
kids-money-manager/
  ├── server/
  │   ├── server.js
  │   └── package.json
  ├── src/
  ├── package.json
  └── railway.json
```

אם המבנה שונה, צריך להתאים את הנתיבים.

## הערות

- Root Directory = `server` אומר ל-Railway שהשירות רץ מתוך תיקיית `server`
- Start Command = `node server.js` אומר ל-Railway להריץ את `server.js` מתוך Root Directory
- אם Root Directory הוא `server`, אז `node server.js` יחפש את הקובץ ב-`server/server.js` (נכון!)

