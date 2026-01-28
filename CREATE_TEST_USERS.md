# יצירת יוזרים לבדיקה לאישור אפל

## מספרי הטלפון הבדיקתיים

- **הורה**: `+1123456789`
- **ילד**: `+1123412345`

## תכונות

כאשר מזינים את המספרים האלה:
- **אין צורך ב-OTP** - המערכת עוקפת את מנגנון האימות
- **כניסה ישירה לדשבורד** - ההורה או הילד נכנסים ישירות לדשבורד הרלוונטי

## יצירת המשתמשים במסד הנתונים

### דרישות

1. MongoDB URI מוגדר ב-`server/.env`:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/kids-money-manager
   ```

### הרצת הסקריפט

```bash
cd server
node create_test_users.js
```

הסקריפט יבצע:
1. חיבור למסד הנתונים
2. בדיקה אם המשתמשים כבר קיימים
3. יצירת משפחה חדשה עם הורה (אם לא קיימת)
4. יצירת ילד במשפחה (אם לא קיים)
5. עדכון קטגוריות לכלול את הילד

### פלט צפוי

```
🔌 Connecting to MongoDB...
✅ Connected to MongoDB

📱 Creating test users:
   Parent: +1123456789
   Child: +1123412345

➕ Creating new parent family...
✅ Family created: family_1234567890_abc123
✅ Child created: ילד בדיקה (child_1234567890_xyz789)

✅ Test users created successfully!

📋 Summary:
   Family ID: family_1234567890_abc123
   Parent Phone: +1123456789
   Child Name: ילד בדיקה
   Child Phone: +1123412345
   Child ID: child_1234567890_xyz789

🔌 MongoDB connection closed

✨ Script completed successfully
```

## שימוש

1. פתח את האפליקציה
2. בחר קידומת ארה"ב (+1)
3. הזן את אחד מהמספרים:
   - `123456789` - להורה
   - `123412345` - לילד
4. המערכת תעבור ישירות לדשבורד הרלוונטי ללא צורך ב-OTP

## הערות

- המספרים האלה עובדים רק במצב בדיקה
- במצב ייצור, יש להסיר את הלוגיקה הזו או לשנות את המספרים
- המספרים מוגדרים ב-`server/server.js` בקבוע `TEST_PHONE_NUMBERS`
