# 🔗 איך לקבל את ה-MongoDB Connection String

## שלב 1: בחר "Drivers"

במסך שאתה רואה, לחץ על **"Drivers"** (האופציה הראשונה).

## שלב 2: בחר Python

אחרי שלחצת על Drivers, תראה מסך עם אפשרויות:
- **Driver:** בחר **Python**
- **Version:** בחר **3.6 or later** (או הגרסה הגבוהה ביותר)

## שלב 3: העתק את ה-Connection String

תראה משהו כמו:
```
mongodb+srv://<username>:<password>@bacharlsraeli.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

**העתק את כל השורה הזו!**

## שלב 4: עדכן את ה-Connection String

1. החלף `<username>` בשם המשתמש שלך ב-MongoDB
2. החלף `<password>` בסיסמה שלך
3. **חשוב:** הוסף את שם ה-database בסוף:
   ```
   mongodb+srv://username:password@bacharlsraeli.xxxxx.mongodb.net/daily_sync?retryWrites=true&w=majority
   ```
   
   שים לב: הוספתי `/daily_sync` לפני ה-`?`

## שלב 5: עדכן את .env

פתח את `daily-sync-backend/.env` ועדכן את השורה:
```
MONGODB_URI=mongodb+srv://username:password@bacharlsraeli.xxxxx.mongodb.net/daily_sync?retryWrites=true&w=majority
```

(החלף עם ה-Connection String האמיתי שלך)

## ✅ סיימת!

אחרי העדכון, השרת יתחבר ל-MongoDB אוטומטית.

---

**💡 טיפ:** אם אתה כבר משתמש ב-MongoDB Atlas לאפליקציית kids-money-manager, אתה יכול להשתמש באותו Connection String, רק שנה את שם ה-database מ-`kids-money-manager` ל-`daily_sync`.
