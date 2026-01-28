# Test Accounts for Apple App Review
# חשבונות בדיקה לבדיקת אפליקציה של אפל

---

## English Version

### Overview

This document describes the test accounts available for Apple App Review. These accounts allow reviewers to test the app's functionality without requiring SMS verification, which is essential for the review process.

### Test Phone Numbers

The following phone numbers are configured as test accounts that bypass SMS OTP (One-Time Password) verification:

#### Parent Account
- **Phone Number**: `+1 123 456 789` (US country code)
- **How to Enter**: Select country code `+1` (USA/Canada), then enter `123456789`
- **Access Level**: Full parent dashboard with all administrative features
- **Purpose**: Allows reviewers to test parent functionality including:
  - Creating and managing children accounts
  - Setting allowances and interest rates
  - Viewing transaction history
  - Managing family finances

#### Child Account
- **Phone Number**: `+1 123 412 345` (US country code)
- **Alternative**: `+1 123 451 234` (US country code)
- **How to Enter**: Select country code `+1` (USA/Canada), then enter `123412345` or `123451234`
- **Access Level**: Child dashboard with limited features
- **Purpose**: Allows reviewers to test child functionality including:
  - Viewing personal balance and transactions
  - Requesting money from parents
  - Viewing allowance schedule

### How to Use Test Accounts

1. **Launch the app** on your device
2. **Select country code**: Tap the flag icon and select `+1` (USA/Canada)
3. **Enter phone number**: 
   - For parent: Enter `123456789`
   - For child: Enter `123412345` or `123451234`
4. **Automatic login**: The app will automatically authenticate without requiring SMS verification
5. **Access dashboard**: You will be redirected directly to the appropriate dashboard (parent or child)

### Technical Details

- **OTP Bypass**: These phone numbers are configured to skip SMS OTP verification for testing purposes
- **Database**: Test accounts are pre-configured in the database
- **Security**: These numbers only work in the production/test environment and are not accessible to regular users
- **Compliance**: This implementation follows Apple's guidelines for providing test accounts for app review

### Important Notes

- These test accounts are **only for Apple App Review purposes**
- The phone numbers are **not real phone numbers** and cannot receive SMS
- The bypass mechanism is **only active for these specific numbers**
- Regular users with real phone numbers will still receive SMS OTP verification as normal

### Support

If you encounter any issues accessing the test accounts, please contact our support team with the following information:
- Device model and iOS version
- Screenshot of the login screen
- Error message (if any)

---

## גרסה עברית

### סקירה כללית

מסמך זה מתאר את חשבונות הבדיקה הזמינים לבדיקת אפליקציה של אפל. חשבונות אלה מאפשרים לבודקים לבדוק את הפונקציונליות של האפליקציה ללא צורך באימות SMS, הנחוץ לתהליך הבדיקה.

### מספרי טלפון לבדיקה

מספרי הטלפון הבאים מוגדרים כחשבונות בדיקה שעוקפים את אימות SMS (קוד אימות חד-פעמי):

#### חשבון הורה
- **מספר טלפון**: `+1 123 456 789` (קידומת ארה"ב)
- **איך להזין**: בחר קידומת `+1` (ארה"ב/קנדה), ואז הזן `123456789`
- **רמת גישה**: דשבורד הורה מלא עם כל התכונות הניהוליות
- **מטרה**: מאפשר לבודקים לבדוק תכונות הורה כולל:
  - יצירה וניהול חשבונות ילדים
  - הגדרת דמי כיס וריבית
  - צפייה בהיסטוריית עסקאות
  - ניהול כספים משפחתיים

#### חשבון ילד
- **מספר טלפון**: `+1 123 412 345` (קידומת ארה"ב)
- **חלופה**: `+1 123 451 234` (קידומת ארה"ב)
- **איך להזין**: בחר קידומת `+1` (ארה"ב/קנדה), ואז הזן `123412345` או `123451234`
- **רמת גישה**: דשבורד ילד עם תכונות מוגבלות
- **מטרה**: מאפשר לבודקים לבדוק תכונות ילד כולל:
  - צפייה במאזן אישי ועסקאות
  - בקשת כסף מההורים
  - צפייה בלוח זמנים של דמי כיס

### איך להשתמש בחשבונות בדיקה

1. **הפעל את האפליקציה** במכשיר שלך
2. **בחר קידומת**: לחץ על אייקון הדגל ובחר `+1` (ארה"ב/קנדה)
3. **הזן מספר טלפון**: 
   - להורה: הזן `123456789`
   - לילד: הזן `123412345` או `123451234`
4. **כניסה אוטומטית**: האפליקציה תאמת אוטומטית ללא צורך באימות SMS
5. **גישה לדשבורד**: תועבר ישירות לדשבורד המתאים (הורה או ילד)

### פרטים טכניים

- **עקיפת OTP**: מספרי טלפון אלה מוגדרים לדלג על אימות SMS OTP למטרות בדיקה
- **מסד נתונים**: חשבונות בדיקה מוגדרים מראש במסד הנתונים
- **אבטחה**: מספרים אלה עובדים רק בסביבת ייצור/בדיקה ואינם נגישים למשתמשים רגילים
- **תאימות**: יישום זה עוקב אחר הנחיות אפל לספק חשבונות בדיקה לבדיקת אפליקציה

### הערות חשובות

- חשבונות בדיקה אלה הם **רק למטרות בדיקת אפליקציה של אפל**
- מספרי הטלפון הם **לא מספרים אמיתיים** ולא יכולים לקבל SMS
- מנגנון העקיפה **פעיל רק למספרים הספציפיים האלה**
- משתמשים רגילים עם מספרי טלפון אמיתיים עדיין יקבלו אימות SMS OTP כרגיל

### תמיכה

אם אתה נתקל בבעיות בגישה לחשבונות הבדיקה, אנא פנה לצוות התמיכה שלנו עם המידע הבא:
- דגם מכשיר וגרסת iOS
- צילום מסך של מסך הכניסה
- הודעת שגיאה (אם יש)

---

## Contact Information / פרטי יצירת קשר

**Email**: support@kidsmoneymanager.app  
**App Name**: Family Bank - Kids Money Manager  
**Version**: 5.1.1

---

*This document is provided for Apple App Review purposes only.*  
*מסמך זה מסופק למטרות בדיקת אפליקציה של אפל בלבד.*
