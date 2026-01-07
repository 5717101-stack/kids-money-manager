# תיקון שגיאת RESEND_API_KEY ב-Railway

## הבעיה
```
Build Failed: build daemon returned an error < failed to solve: secret RESEND_API_KEY not found >
```

## הפתרון

Railway מנסה לטעון את `RESEND_API_KEY` ב-build time, אבל הוא צריך להיות רק ב-runtime.

### שלב 1: הוסף את המשתנה ב-Railway

1. לך ל-Railway Dashboard → Service → Variables
2. לחץ **"New Variable"**
3. הוסף:
   - **Name:** `RESEND_API_KEY`
   - **Value:** `re_xxxxxxxxxxxxxxxxxxxxx` (ה-API Key מ-Resend)
   - **⚠️ חשוב:** אל תסמן את זה כ-"Secret" או "Build-time variable"
4. לחץ **"Add"**

4. הוסף גם:
   - **Name:** `RESEND_FROM_EMAIL`
   - **Value:** `onboarding@resend.dev` (או domain מותאם)
   - **⚠️ חשוב:** אל תסמן את זה כ-"Secret" או "Build-time variable"
5. לחץ **"Add"**

### שלב 2: ודא שהמשתנים הם Runtime Variables

1. ב-Variables, ודא ש-`RESEND_API_KEY` ו-`RESEND_FROM_EMAIL` **לא** מסומנים כ:
   - ❌ "Build-time variable"
   - ❌ "Secret" (אלא אם כן באמת צריך)
   
2. הם צריכים להיות **Runtime Variables** בלבד

### שלב 3: Redeploy

1. לחץ **"Deployments"**
2. לחץ **"..."** → **"Redeploy"**
3. המתן 2-3 דקות

## אם עדיין יש בעיה

אם עדיין מקבלים את השגיאה, נסה:

1. **מחק את המשתנה** `RESEND_API_KEY` מה-Variables
2. **צור אותו מחדש** - הפעם ודא שהוא **לא** מסומן כ-Build-time variable
3. **Redeploy**

## הערות

- `RESEND_API_KEY` צריך להיות **Runtime Variable** בלבד
- הוא לא צריך להיות זמין ב-build time
- הקוד בודק אם המשתנה קיים לפני שהוא מנסה להשתמש בו

