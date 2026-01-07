# הגדרת Resend לשליחת מיילים

## שלב 1: יצירת חשבון ב-Resend

1. לך ל-https://resend.com
2. לחץ על "Sign Up" ויצור חשבון (חינם - 100 מיילים ביום)
3. אשר את המייל שלך

## שלב 2: יצירת API Key

1. אחרי ההתחברות, לך ל-Dashboard
2. לחץ על "API Keys" בתפריט
3. לחץ על "Create API Key"
4. תן שם (למשל: "Kids Money Manager Production")
5. העתק את ה-API Key (תראה אותו רק פעם אחת!)

## שלב 3: הגדרת Domain (אופציונלי - לפרודקשן)

**לפיתוח/בדיקה:**
- Resend מספק domain לבדיקה: `onboarding@resend.dev`
- אפשר להשתמש בו לבדיקות

**לפרודקשן:**
1. לך ל-"Domains" ב-Resend Dashboard
2. לחץ על "Add Domain"
3. הכנס את ה-domain שלך (למשל: `kidsmoneymanager.app`)
4. הוסף את ה-DNS records שהם נותנים לך
5. אחרי ה-verification, תוכל להשתמש במייל כמו `noreply@kidsmoneymanager.app`

## שלב 4: הגדרת משתני סביבה ב-Railway

1. לך ל-Railway Dashboard → הפרויקט שלך → ה-Service (Backend)
2. לחץ על "Variables" (או "Environment Variables")
3. הוסף את המשתנים הבאים:

```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@kidsmoneymanager.app
```

**לפיתוח/בדיקה:**
```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```

## שלב 5: Deploy

1. אחרי הוספת המשתנים, Railway יתחיל rebuild אוטומטית
2. בדוק את ה-Logs ב-Railway - אמור לראות:
   ```
   [RESEND] ✅ Client initialized successfully
   ```

## בדיקה

1. נסה לשלוח OTP מהאפליקציה
2. בדוק את ה-Logs ב-Railway - אמור לראות:
   ```
   [EMAIL] ✅ Email sent successfully!
   ```
3. בדוק את תיבת המייל שלך (וגם spam folder)

## בעיות נפוצות

### "Email not sent"
- בדוק שה-API Key נכון
- בדוק שה-From Email מאומת (או משתמש ב-onboarding@resend.dev)
- בדוק את ה-Logs ב-Railway לפרטים

### "Domain not verified"
- אם אתה משתמש ב-domain מותאם, ודא שה-DNS records מוגדרים נכון
- השתמש ב-`onboarding@resend.dev` לבדיקות

### "Rate limit exceeded"
- Free tier: 100 מיילים ביום
- אם צריך יותר, שדרג ל-paid plan

## קישורים שימושיים

- Resend Dashboard: https://resend.com/emails
- Documentation: https://resend.com/docs
- API Reference: https://resend.com/docs/api-reference

