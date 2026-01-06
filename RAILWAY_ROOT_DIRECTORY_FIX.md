# תיקון: הגדרת Root Directory ב-Railway

## הבעיה
Railway מחפש את הקובץ ב-`/app/server/server.js` אבל לא מוצא אותו.

## הפתרון
צריך להגדיר את ה-Root Directory ב-Railway Dashboard ל-`server`.

## שלבים

1. **היכנס ל-Railway Dashboard**
   - לך לפרויקט שלך
   - בחר את השירות `kids-money-manager-server`

2. **Settings → Root Directory**
   - לחץ על Settings
   - מצא את "Root Directory"
   - שנה אותו ל: `server`
   - שמור

3. **Start Command**
   - ודא ש-Start Command הוא: `npm start`
   - זה יעבוד כי עכשיו Railway יודע שהוא בתיקיית `server`

4. **Redeploy**
   - לחץ על "Redeploy" או המתן ל-auto deploy
   - השרת אמור להתחיל בהצלחה

## למה זה עובד?
- Railway מריץ את הפקודות מתוך ה-Root Directory
- אם Root Directory הוא `server`, אז `npm start` יריץ את `server/package.json`
- זה יקרא ל-`node server.js` מתוך התיקייה הנכונה

## אם עדיין לא עובד
אם עדיין יש בעיות, נסה:
1. בדוק את הלוגים ב-Railway
2. ודא ש-`server/package.json` קיים ויש בו `"start": "node server.js"`
3. ודא ש-`server/server.js` קיים

