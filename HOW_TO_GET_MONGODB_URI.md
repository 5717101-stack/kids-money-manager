# איך לקבל את ה-MongoDB Connection String

## אופציה 1: מהמחשב במשרד (הקלה ביותר)

1. במחשב במשרד, פתח את התיקייה של הפרויקט
2. פתח את הקובץ `server/.env`
3. העתק את השורה שמתחילה ב-`MONGODB_URI=`
4. במחשב הזה, הרץ:
   ```bash
   cd ~/Projects/kids-money-manager/server
   ./setup_mongodb.sh
   ```
5. הדבק את ה-connection string כשהוא מבקש

## אופציה 2: מ-MongoDB Atlas

אם יש לך גישה ל-MongoDB Atlas:

1. היכנס ל-[MongoDB Atlas](https://cloud.mongodb.com/)
2. בחר את ה-Cluster שלך
3. לחץ על **"Connect"**
4. בחר **"Connect your application"**
5. בחר Driver: **Node.js** ו-Version: **5.5 or later**
6. העתק את ה-Connection String
7. החלף `<username>` ו-`<password>` בערכים שלך
8. הוסף בסוף: `/kids-money-manager`
9. דוגמה לתוצאה:
   ```
   mongodb+srv://myuser:mypassword@cluster0.xxxxx.mongodb.net/kids-money-manager?retryWrites=true&w=majority
   ```

## אופציה 3: יצירה ידנית

אם אתה יודע את הפרטים:

```bash
cd ~/Projects/kids-money-manager/server
cat > .env << 'ENVEOF'
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/kids-money-manager
PORT=3001
ENVEOF
```

החלף:
- `username` - שם המשתמש ב-MongoDB
- `password` - הסיסמה
- `cluster.mongodb.net` - כתובת ה-cluster שלך

## לאחר ההגדרה

הפעל מחדש את השרת:

```bash
# עצור את השרת הנוכחי
pkill -f "node.*server.js"

# הפעל מחדש
export PATH="$HOME/.local/node/bin:$PATH"
cd ~/Projects/kids-money-manager
npm run dev:all
```

בדוק בלוגים שאתה רואה: `Connected to MongoDB`
