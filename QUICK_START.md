# התחלה מהירה

## הרצה מקומית

### 1. התקן תלויות
```bash
# Frontend
npm install

# Backend
cd server
npm install
cd ..
```

### 2. הרץ את האפליקציה

**אפשרות 1: עם MongoDB (מומלץ)**
1. התקן MongoDB או השתמש ב-MongoDB Atlas
2. צור `server/.env`:
   ```
   MONGODB_URI=mongodb://localhost:27017/kids-money-manager
   PORT=3001
   ```
3. הרץ:
   ```bash
   # חלון 1 - Backend
   cd server
   npm run dev
   
   # חלון 2 - Frontend
   npm run dev
   ```

**אפשרות 2: ללא MongoDB (בדיקה בלבד)**
```bash
# חלון 1 - Backend (יעבוד עם אחסון זמני)
cd server
npm run dev

# חלון 2 - Frontend
npm run dev
```

### 3. פתח בדפדפן
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001/api/health

## פרסום באינטרנט

ראה [מדריך מהיר](DEPLOYMENT_QUICK.md) או [מדריך מפורט](DEPLOYMENT.md)

