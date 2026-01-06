# הגדרת MongoDB לפרויקט

## מצב נוכחי

הפרויקט רץ עם אחסון זמני בזיכרון כי אין קובץ `.env` עם הגדרות MongoDB.

## מה צריך לעשות

### אופציה 1: אם יש לך MongoDB Atlas (מומלץ)

1. **קבל את ה-connection string** מהמחשב במשרד:
   - במחשב במשרד, פתח את `server/.env`
   - העתק את ה-`MONGODB_URI`

2. **צור קובץ `.env` בשרת:**
   ```bash
   cd ~/Projects/kids-money-manager/server
   nano .env
   ```

3. **הוסף את ההגדרות:**
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/kids-money-manager
   PORT=3001
   ```

4. **הפעל מחדש את השרת:**
   ```bash
   # עצור את השרת הנוכחי
   pkill -f "node.*server.js"
   
   # הפעל מחדש
   export PATH="$HOME/.local/node/bin:$PATH"
   cd ~/Projects/kids-money-manager
   npm run dev:all
   ```

### אופציה 2: אם יש MongoDB מקומי

אם יש לך MongoDB מותקן מקומית:

```bash
cd ~/Projects/kids-money-manager/server
cat > .env << 'ENVEOF'
MONGODB_URI=mongodb://localhost:27017/kids-money-manager
PORT=3001
ENVEOF
```

### אופציה 3: העתק את הקובץ מהמחשב במשרד

אם יש לך גישה למחשב במשרד:

1. העתק את `server/.env` מהמחשב במשרד
2. שמור אותו ב-`~/Projects/kids-money-manager/server/.env`

## בדיקה

לאחר יצירת הקובץ, השרת יתחבר אוטומטית ל-MongoDB ויטען את הנתונים הקיימים.

בדוק בלוגים:
```bash
cat /tmp/project.log | grep -i "mongo\|connected"
```

אמור לראות: `Connected to MongoDB`
