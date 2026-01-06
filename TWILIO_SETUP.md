# הגדרת Twilio ל-SMS

## שלב 1: יצירת חשבון Twilio

1. לך ל-https://www.twilio.com/try-twilio
2. הירשם (חינם - מקבל $15.50 קרדיט)
3. אמת את מספר הטלפון שלך

## שלב 2: קבלת פרטי ההתחברות

1. אחרי ההרשמה, לך ל-Dashboard
2. תראה את:
   - **Account SID** - זה המזהה של החשבון שלך
   - **Auth Token** - זה הסיסמה (לחץ על "View" כדי לראות)

## שלב 3: רכישת מספר טלפון

1. ב-Dashboard, לך ל-Phone Numbers > Manage > Buy a number
2. בחר:
   - **Country**: Israel (או מדינה אחרת)
   - **Capabilities**: SMS (חובה!)
3. לחץ "Search" ובחר מספר
4. לחץ "Buy" (עולה בערך $1/חודש)

## שלב 4: הוספת משתני סביבה ב-Railway

1. לך ל-Railway Dashboard: https://railway.app
2. בחר את הפרויקט שלך (kids-money-manager)
3. לחץ על ה-Service של ה-backend
4. לך ל-Tab "Variables"
5. הוסף 3 משתנים חדשים:

   **TWILIO_ACCOUNT_SID**
   - Value: [העתק את Account SID מ-Twilio]

   **TWILIO_AUTH_TOKEN**
   - Value: [העתק את Auth Token מ-Twilio]

   **TWILIO_PHONE_NUMBER**
   - Value: [המספר שרכשת, בפורמט +972XXXXXXXXX]

6. לחץ "Add" לכל משתנה
7. Railway יבצע restart אוטומטי

## שלב 5: בדיקה

1. נסה להריץ את האפליקציה
2. הכנס מספר טלפון
3. אתה אמור לקבל SMS עם קוד OTP!

## הערות חשובות:

- **בפיתוח מקומי**: SMS יודפס לקונסול (לא נשלח באמת)
- **בפרודקשן**: SMS נשלח באמת רק אם הגדרת את Twilio ב-Railway
- **עלויות**: 
  - מספר טלפון: ~$1/חודש
  - SMS: ~$0.01-0.05 לכל SMS (תלוי במדינה)
  - עם $15.50 קרדיט חינם יש לך מספיק לבדיקות

## פתרון בעיות:

אם SMS לא נשלח:
1. בדוק שהמשתנים ב-Railway נכונים
2. בדוק שהמספר שרכשת תומך ב-SMS
3. בדוק את ה-Logs ב-Railway לראות שגיאות
4. ודא שהמספר בפורמט נכון (+972XXXXXXXXX)

