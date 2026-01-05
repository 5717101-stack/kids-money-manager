# כפיית עדכון ב-Railway

## הבעיה
הקוד המקומי נכון (0.0.0.0), אבל Railway עדיין רואה את הקוד הישן (localhost:3001).

## פתרון: כפיית עדכון

### שלב 1: ודא שהקוד ב-GitHub מעודכן
1. היכנס ל-GitHub
2. פתח את ה-repository
3. בדוק את הקובץ `server/server.js`
4. ודא ששורה 314 אומרת: `Server running on http://0.0.0.0:${PORT}`

### שלב 2: כפיית Redeploy ב-Railway

**אפשרות 1: דרך ה-Dashboard**
1. היכנס ל-Railway Dashboard
2. לחץ על ה-Service
3. לחץ **"Settings"**
4. גלול למטה ל-**"Danger Zone"**
5. לחץ **"Clear Build Cache"**
6. לחץ **"Deployments"**
7. לחץ על ה-Deployment האחרון
8. לחץ **"..."** → **"Redeploy"**

**אפשרות 2: דרך GitHub (מומלץ)**
1. פתח את ה-repository ב-GitHub
2. ערוך קובץ כלשהו (למשל README.md)
3. הוסף שורה ריקה
4. Commit & Push
5. Railway יתעדכן אוטומטית

**אפשרות 3: מחק וצור מחדש**
1. ב-Railway, מחק את ה-Service
2. צור Service חדש מה-GitHub repository
3. ודא ש-Root Directory = `server`
4. ודא ש-Start Command = `npm start`
5. הוסף משתני סביבה

### שלב 3: בדוק את ה-Logs
אחרי ה-Redeploy, בדוק את ה-Logs. צריך לראות:
```
Server running on http://0.0.0.0:3001
```

אם עדיין רואה `localhost:3001` - יש בעיה.

## אם עדיין לא עובד

1. **בדוק את ה-GitHub repository:**
   - האם הקוד שם מעודכן?
   - האם Railway מחובר ל-repository הנכון?

2. **בדוק את ההגדרות ב-Railway:**
   - Root Directory = `server`?
   - Start Command = `npm start`?
   - האם יש משתני סביבה?

3. **נסה Clear Cache:**
   - Settings → Danger Zone → Clear Build Cache
   - Redeploy

## לגבי הגרסה

הגרסה (1.01) מופיעה בתחתית המסך. אם אתה לא רואה אותה:
1. ודא שה-frontend התעדכן ב-Vercel
2. נקה את ה-Cache בדפדפן (Ctrl+Shift+R)
3. בדוק את ה-Console (F12) לשגיאות


