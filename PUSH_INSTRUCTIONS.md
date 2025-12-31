# הוראות דחיפה ל-GitHub

## הבעיה
הקוד לא נדחף ל-GitHub, ולכן Railway לא מתעדכן.

## מה לעשות

### שלב 1: עדכן את ה-remote (אם צריך)
אם ה-remote עדיין מצביע על `YOUR_USERNAME`, עדכן אותו:

```bash
cd "/Users/itzikbachar/Test Cursor"
git remote set-url origin https://github.com/YOUR_ACTUAL_USERNAME/kids-money-manager.git
```

החלף `YOUR_ACTUAL_USERNAME` בשם המשתמש האמיתי שלך ב-GitHub.

### שלב 2: דחוף את השינויים
```bash
git push --set-upstream origin main
```

או אם כבר יש upstream:
```bash
git push
```

### שלב 3: המתן ל-Railway להתעדכן
Railway יתעדכן אוטומטית תוך 1-2 דקות.

### שלב 4: בדוק את ה-Logs
אחרי ה-update, ב-Logs צריך להיות:
```
Server running on http://0.0.0.0:3001
```

## אם יש שגיאות

### שגיאה: "remote origin already exists"
זה בסדר, המשך ל-push.

### שגיאה: "authentication failed"
1. ודא שיש לך הרשאות ל-repository
2. נסה להשתמש ב-Personal Access Token במקום סיסמה

### שגיאה: "repository not found"
1. ודא שה-repository קיים ב-GitHub
2. ודא שה-URL נכון

