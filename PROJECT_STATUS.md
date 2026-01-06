# סטטוס הפרויקט - Kids Money Manager

## ✅ מה שהושלם:

1. ✅ **הפרויקט הורד מ-GitHub** - `https://github.com/5717101-stack/kids-money-manager.git`
2. ✅ **הפרויקט נמצא ב:** `~/Projects/kids-money-manager`
3. ✅ **מבנה הפרויקט נבדק:**
   - Frontend: React + Vite
   - Backend: Node.js + Express
   - Database: MongoDB (אופציונלי)

## ⏳ מה שצריך לעשות:

### 1. התקן Node.js (נדרש)

**הדרך הקלה:**
1. גש ל: https://nodejs.org/
2. הורד את הגרסה LTS (Long Term Support)
3. התקן את הקובץ
4. בדוק: `node --version` ו-`npm --version`

### 2. התקן Dependencies

לאחר התקנת Node.js:

```bash
cd ~/Projects/kids-money-manager
npm install
cd server
npm install
cd ..
```

### 3. הרץ את הפרויקט

```bash
cd ~/Projects/kids-money-manager
npm run dev:all
```

האפליקציה תרוץ על:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:3001

**סיסמת הורה:** `2016`

## 📁 קבצי עזרה שנוצרו:

- `QUICK_START.md` - התחלה מהירה
- `SETUP_INSTRUCTIONS.md` - הוראות מפורטות
- `INSTALL_NODE.md` - הוראות התקנת Node.js

## 📝 הערות:

- הפרויקט יכול לעבוד עם MongoDB או עם אחסון זמני בזיכרון
- אם אין MongoDB, הנתונים יאבדו בסגירת השרת
- הסינכרון מתבצע אוטומטית כל 5 שניות

## 🎯 הצעדים הבאים:

1. התקן Node.js (ראה `INSTALL_NODE.md`)
2. הרץ `npm install` בשתי התיקיות
3. הרץ `npm run dev:all` להרצת הפרויקט
4. פתח http://localhost:5173 בדפדפן
