# הוראות הגדרה - Kids Money Manager

## ✅ מה שכבר בוצע:

1. ✅ הפרויקט הורד מ-GitHub
2. ✅ הפרויקט נמצא ב: `~/Projects/kids-money-manager`

## ⏳ מה שצריך לעשות:

### 1. התקן Node.js

**הדרך הקלה ביותר:**
1. פתח דפדפן וגש ל: https://nodejs.org/
2. הורד את הגרסה LTS (Long Term Support) למחשב
3. התקן את הקובץ שהורדת (פשוט פתח את הקובץ ועקוב אחר ההוראות)
4. בדוק שההתקנה הצליחה:
   ```bash
   node --version
   npm --version
   ```

### 2. התקן Dependencies

לאחר התקנת Node.js, הרץ:

```bash
cd ~/Projects/kids-money-manager

# התקן dependencies של frontend
npm install

# התקן dependencies של backend
cd server
npm install
cd ..
```

### 3. הגדר MongoDB (אופציונלי)

הפרויקט יכול לעבוד עם MongoDB או עם אחסון זמני בזיכרון.

**אם יש לך MongoDB:**
צור קובץ `server/.env`:
```
MONGODB_URI=mongodb://localhost:27017/kids-money-manager
PORT=3001
```

**אם אין לך MongoDB:**
השרת יעבוד עם אחסון זמני בזיכרון (הנתונים יאבדו בסגירת השרת).

### 4. הרץ את הפרויקט

**בחלונות נפרדים:**

```bash
# חלון 1 - Backend
cd ~/Projects/kids-money-manager/server
npm run dev

# חלון 2 - Frontend
cd ~/Projects/kids-money-manager
npm run dev
```

**או עם פקודה אחת:**

```bash
cd ~/Projects/kids-money-manager
npm run dev:all
```

האפליקציה תרוץ על:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

## 📝 הערות:

- הסיסמה להורה היא: `2016`
- הנתונים מסתנכרנים אוטומטית כל 5 שניות
- אם אין MongoDB, הנתונים נשמרים רק בזיכרון (יאבדו בסגירת השרת)

## 🔧 פתרון בעיות:

**אם npm install נכשל:**
- ודא ש-Node.js מותקן: `node --version`
- נסה למחוק את `node_modules` ולהריץ שוב: `rm -rf node_modules && npm install`

**אם השרת לא עובד:**
- בדוק שהפורט 3001 פנוי
- בדוק את קובץ `server/.env` אם יש MongoDB

**אם Frontend לא עובד:**
- בדוק שהפורט 5173 פנוי
- בדוק את הקונסול בדפדפן לשגיאות
