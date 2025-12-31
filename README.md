# אפליקציית ניהול כסף לילדים

אפליקציית ווב לניהול כסף של שני ילדים עם סינכרון מלא בין כל המכשירים.

## 📚 מדריכי פרסום

- **[מדריך מהיר (5 דקות)](DEPLOYMENT_QUICK.md)** - לפרסום מהיר
- **[מדריך מפורט](DEPLOYMENT.md)** - מדריך שלב אחר שלב עם הסברים

## תכונות

- ✅ ממשק הורה עם סיסמה (2016)
- ✅ ממשק ילדים נפרד לכל ילד
- ✅ סינכרון מלא - כל המכשירים רואים את אותם נתונים
- ✅ הוספת כסף והוצאות עם תיאור
- ✅ תצוגת יתרה ופעולות אחרונות

## התקנה והרצה

### 1. התקן תלויות

```bash
# תלויות frontend
npm install

# תלויות backend
cd server
npm install
cd ..
```

### 2. הגדר MongoDB

**אפשרות 1: MongoDB Atlas (מומלץ לפרודקשן)**
1. הירשם ל-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (חינמי)
2. צור cluster חדש
3. קבל את ה-connection string
4. צור קובץ `server/.env`:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/kids-money-manager
   PORT=3001
   ```

**אפשרות 2: MongoDB מקומי**
1. התקן MongoDB על המחשב שלך
2. צור קובץ `server/.env`:
   ```
   MONGODB_URI=mongodb://localhost:27017/kids-money-manager
   PORT=3001
   ```

**אפשרות 3: ללא MongoDB (בדיקה בלבד)**
- השרת יעבוד עם אחסון זמני בזיכרון (לא מומלץ לפרודקשן)

### 3. הרץ את האפליקציה

**בחלונות נפרדים:**

```bash
# חלון 1 - Backend
cd server
npm run dev

# חלון 2 - Frontend
npm run dev
```

**או עם פקודה אחת (דורש concurrently):**

```bash
npm run dev:all
```

האפליקציה תרוץ על:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

## בנייה לפרודקשן

```bash
# בניית frontend
npm run build

# השרת כבר מוכן לפרודקשן
cd server
npm start
```

## פרסום באינטרנט

### Frontend (Vercel/Netlify)

1. העלה את הקוד ל-GitHub
2. פרסם דרך Vercel או Netlify
3. הגדר משתנה סביבה: `VITE_API_URL=https://your-backend-url.com/api`

### Backend (Railway/Render/MongoDB Atlas)

**Railway (מומלץ):**
1. הירשם ל-[Railway](https://railway.app) (חינמי)
2. הוסף MongoDB Atlas service
3. הוסף Node.js service מה-GitHub repository
4. הגדר `MONGODB_URI` מ-MongoDB Atlas
5. Railway יפרסם אוטומטית

**Render:**
1. הירשם ל-[Render](https://render.com) (חינמי)
2. צור Web Service מה-GitHub repository
3. הגדר `MONGODB_URI` מ-MongoDB Atlas
4. Render יפרסם אוטומטית

## שינוי סיסמה

הסיסמה מוגדרת ב-`src/components/ParentLogin.jsx`:
```js
const PARENT_PASSWORD = '2016';
```

## מבנה הפרויקט

```
/
├── src/              # Frontend (React)
├── server/           # Backend (Express + MongoDB)
├── package.json      # Frontend dependencies
└── server/package.json  # Backend dependencies
```

## API Endpoints

- `GET /api/children` - קבלת כל הילדים
- `GET /api/children/:childId` - קבלת ילד ספציפי
- `GET /api/children/:childId/transactions?limit=N` - פעולות של ילד
- `POST /api/transactions` - הוספת פעולה חדשה
- `GET /api/health` - בדיקת סטטוס

## הערות

- הנתונים נשמרים ב-MongoDB וזמינים מכל מכשיר
- הסיסמה נשמרת ב-sessionStorage (נמחקת בסגירת הדפדפן)
- ממשקי הילדים מתעדכנים אוטומטית כל 5 שניות
