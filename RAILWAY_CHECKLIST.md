# Checklist - Railway Service Offline

## בדיקה מהירה - שלב אחר שלב

### ✅ שלב 1: בדוק אם יש Service בכלל

1. היכנס ל-Railway Dashboard
2. לחץ על הפרויקט שלך
3. **האם אתה רואה Service?**
   - אם לא → צור Service חדש (ראה למטה)
   - אם כן → המשך לשלב 2

### ✅ שלב 2: בדוק את ההגדרות

לחץ על ה-Service → **Settings**

**Root Directory:**
- [ ] מוגדר ל-`server`?
- אם לא → שנה ל-`server` ושמור

**Start Command:**
- [ ] מוגדר ל-`npm start`?
- אם לא → שנה ל-`npm start` ושמור

**Build Command:**
- [ ] יכול להיות ריק או `npm install`
- לא חובה, אבל יכול לעזור

### ✅ שלב 3: בדוק את משתני הסביבה

לחץ **Variables**

**חייב להיות:**
- [ ] `MONGODB_URI` - עם Connection String מלא
- [ ] `PORT` - עם הערך `3001`

אם חסר אחד מהם → הוסף אותו!

### ✅ שלב 4: בדוק את ה-Deployments

1. לחץ **Deployments**
2. **האם יש Deployment?**
   - אם לא → צריך ליצור Deployment חדש
   - אם כן → לחץ עליו ובדוק את ה-Logs

### ✅ שלב 5: אם אין Deployment - צור אחד

1. לחץ על ה-Service
2. לחץ **"Deploy"** או **"Redeploy"**
3. המתן 2-3 דקות
4. בדוק שוב את ה-Logs

## אם עדיין לא עובד - פתרון מלא

### פתרון 1: מחק וצור מחדש

1. **מחק את ה-Service:**
   - Settings → Delete Service
   - אשר

2. **צור Service חדש:**
   - New → GitHub Repo
   - בחר את ה-repository
   - לחץ Deploy

3. **מיד אחרי יצירת ה-Service:**
   - Settings → Root Directory: `server`
   - Settings → Start Command: `npm start`
   - Variables → הוסף `MONGODB_URI` ו-`PORT`
   - שמור הכל

4. **Redeploy:**
   - Deployments → ... → Redeploy

### פתרון 2: בדוק את ה-Repository

1. ודא שהקוד ב-GitHub:
   - יש תיקיית `server/`
   - יש `server/package.json`
   - יש `server/server.js`

2. אם לא → העלה את הקוד:
   ```bash
   git add .
   git commit -m "Add server files"
   git push
   ```

### פתרון 3: בדוק את ה-Logs ב-GitHub Actions

אם Railway משתמש ב-GitHub Actions:
1. היכנס ל-GitHub
2. לחץ על ה-Repository
3. לחץ **Actions**
4. בדוק אם יש שגיאות

## מה לבדוק עכשיו

1. **האם יש Service בפרויקט?**
   - אם לא → צור אחד

2. **מה ההגדרות של ה-Service?**
   - Root Directory = `server`?
   - Start Command = `npm start`?

3. **מה משתני הסביבה?**
   - `MONGODB_URI` קיים?
   - `PORT` קיים?

4. **האם יש Deployment?**
   - אם לא → לחץ Deploy/Redeploy

5. **מה כתוב ב-Logs?**
   - אם אין לוגים → השרת לא התחיל בכלל

## אם אין לוגים בכלל

זה אומר שהשרת לא התחיל. הסיבות הנפוצות:

1. **Root Directory לא נכון**
   - ודא שהוא `server`

2. **Start Command לא נכון**
   - ודא שהוא `npm start`

3. **אין package.json**
   - ודא ש-`server/package.json` קיים ב-GitHub

4. **הקוד לא ב-GitHub**
   - ודא שהעלית את כל הקבצים

## צעדים הבאים

1. **בדוק את כל ה-✅ למעלה**
2. **אם משהו לא נכון - תקן אותו**
3. **Redeploy**
4. **המתן 2-3 דקות**
5. **בדוק שוב**

## אם עדיין לא עובד

שלח לי:
1. צילום מסך של ה-Settings (Root Directory, Start Command)
2. צילום מסך של ה-Variables
3. צילום מסך של ה-Deployments
4. מה כתוב ב-Logs (אם יש)

ואני אעזור לך לפתור!

