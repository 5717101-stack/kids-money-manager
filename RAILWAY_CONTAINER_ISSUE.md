# פתרון בעיית Container שנעצר ב-Railway

## הבעיה
הקונטיינר נעצר מיד אחרי ההתחלה עם `SIGTERM`, למרות שהשרת התחיל בהצלחה.

## מה עשיתי

### 1. שיפור Error Handling של SMS
- הוספתי לוגים מפורטים יותר לשגיאות SMS
- השרת יציג את קוד השגיאה ופרטים נוספים
- השרת לא יקרוס אם SMS נכשל

### 2. הוספת Handlers ל-Errors
- `uncaughtException` - לא יקרוס את השרת
- `unhandledRejection` - ירשום לוג אבל לא יקרוס
- שיפור ה-SIGTERM handler

### 3. הוספת Twilio ל-package.json
- ודא ש-Twilio מותקן ב-Railway

## מה לבדוק עכשיו

### 1. בדוק את הלוגים החדשים
אחרי ה-deploy, הלוגים יציגו:
- ✅ אם SMS נשלח בהצלחה: `SMS sent successfully to +972...`
- ❌ אם יש שגיאה: `Error sending SMS:` עם פרטים

### 2. שגיאות נפוצות של Twilio

**21211 - Invalid 'To' Phone Number**
- המספר לא תקין
- צריך להיות בפורמט: `+972505717101` (עם +)

**21608 - Unsubscribed recipient**
- המספר לא רשום ב-Twilio
- צריך להוסיף את המספר ב-Twilio Console → Phone Numbers → Verified Caller IDs

**21614 - Unsubscribed recipient**
- אותו דבר - צריך לאמת את המספר

**30008 - Unknown destination handset**
- המספר לא קיים או לא פעיל

### 3. בדוק את Twilio Console
1. היכנס ל: https://console.twilio.com
2. לך ל-Monitor → Logs → Errors
3. חפש שגיאות שנשלחו

### 4. ודא שהמספר מאומת
אם אתה ב-Trial Account:
1. Twilio Console → Phone Numbers → Verified Caller IDs
2. הוסף את המספר שלך
3. תקבל קוד אימות ב-SMS
4. הכנס את הקוד

## אם עדיין לא עובד

1. **בדוק את הלוגים החדשים** - עכשיו תראה בדיוק מה השגיאה
2. **בדוק את Twilio Console** - שם תראה את כל השגיאות
3. **ודא שהמספר מאומת** - אם אתה ב-Trial Account

## הערות

- השרת לא יקרוס אם SMS נכשל - הוא רק ירשום שגיאה
- הלוגים עכשיו מפורטים יותר - תראה בדיוק מה השגיאה
- אם המספר לא מאומת ב-Twilio, תקבל שגיאה 21608 או 21614

