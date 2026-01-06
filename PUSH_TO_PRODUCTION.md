# איך לדחוף את הגרסה 2.7 לפרודקשן

## המצב:
✅ הקוד מוכן לדחיפה
✅ כל השינויים קיימים
❌ צריך לדחוף ל-GitHub (דורש credentials)

## דרכים לדחיפה:

### דרך 1: דרך Terminal (אם יש לך credentials)
```bash
cd ~/Projects/kids-money-manager
git push origin main
```

### דרך 2: דרך GitHub Desktop
1. פתח GitHub Desktop
2. בחר את הפרויקט
3. לחץ "Push origin"

### דרך 3: דרך GitHub Web Interface
1. לך ל: https://github.com/5717101-stack/kids-money-manager
2. לחץ "Upload files"
3. העלה את הקבצים שהשתנו

### דרך 4: Personal Access Token
אם יש לך Personal Access Token:
```bash
git push https://YOUR_TOKEN@github.com/5717101-stack/kids-money-manager.git main
```

## אחרי ה-push:

1. **Vercel** יעשה deploy אוטומטי (2-3 דקות)
2. **Railway** יעשה deploy אוטומטי (1-2 דקות)

## בדיקה:

- לך ל-Vercel Dashboard → תראה deploy חדש
- לך ל-Railway Dashboard → תראה deploy חדש
- נסה את האפליקציה → תראה דף בחירה חדש

## מה כלול בגרסה 2.7:

✅ מערכת OTP עם SMS
✅ משפחות מרובות  
✅ דף בחירה ראשוני
✅ דף הרשמה עם מספר טלפון
✅ דף אימות OTP
✅ הקמת ילדים עם קודי הצטרפות
✅ שחזור סיסמה לילד
