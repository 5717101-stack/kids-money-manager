# בדיקת הגדרות Twilio ב-Railway

## בעיה: לא מקבלים SMS

### שלב 1: בדוק את הלוגים של Railway

1. היכנס ל-Railway Dashboard: https://railway.app
2. בחר את הפרויקט `kids-money-manager`
3. בחר את השירות `kids-money-manager-server`
4. לחץ על "Deployments" או "Logs"
5. חפש את ההודעה הבאה:

**אם רואה:**
```
✅ Twilio SMS service initialized
   Account SID: AC0d2901a5...
   Phone Number: +972505717101
```
✅ **Twilio מוגדר נכון!**

**אם רואה:**
```
⚠️  Twilio not configured - SMS will be logged to console only
   Missing: TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_PHONE_NUMBER
```
❌ **המשתנים לא מוגדרים!**

### שלב 2: הוסף/בדוק משתני סביבה ב-Railway

1. ב-Railway Dashboard, בחר את השירות `kids-money-manager-server`
2. לחץ על "Variables" או "Environment"
3. ודא שיש את המשתנים הבאים:

```
TWILIO_ACCOUNT_SID=[TWILIO_ACCOUNT_SID]
TWILIO_AUTH_TOKEN=7615faec6cdbdc0159325c448ba5fe68
TWILIO_PHONE_NUMBER=+972505717101
```

4. אם המשתנים לא קיימים, לחץ על "New Variable" והוסף אותם
5. אחרי הוספה/עדכון, Railway יעשה redeploy אוטומטי

### שלב 3: בדוק את הטלפון

- ודא שהמספר שלך נכון (כולל קידומת המדינה)
- בדוק את תיבת הספאם
- נסה לשלוח שוב

### שלב 4: בדוק את Twilio Console

1. היכנס ל-Twilio Console: https://console.twilio.com
2. בדוק את ה-"Logs" או "Monitor" → "Logs"
3. חפש הודעות שנשלחו למספר שלך

### הערות

- אם המשתנים לא מוגדרים, השרת ירשום את ה-SMS בקונסול אבל לא ישלח אותו
- אחרי הוספת משתנים, צריך לחכות 1-2 דקות ל-redeploy

