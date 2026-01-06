# איך לאשר Developer ב-iPhone

## הבעיה:
כשמנסים להריץ אפליקציה על iPhone, הוא אומר שהטלפון לא מאשר.

## הפתרון:

### שלב 1: הרץ את האפליקציה ב-Xcode
1. חבר את ה-iPhone למחשב
2. ב-Xcode, בחר את ה-iPhone שלך (לא Simulator)
3. לחץ Run (▶️)
4. האפליקציה תותקן על ה-iPhone אבל לא תיפתח

### שלב 2: אמת את המפתח ב-iPhone

1. **פתח Settings ב-iPhone**
2. **לך ל-General**
3. **גלול למטה ולך ל-VPN & Device Management**
   (או "Device Management" או "Profiles & Device Management")
4. **תראה "Developer App"** עם השם שלך או "Apple Development"
5. **לחץ על זה**
6. **לחץ "Trust [Your Name]"** או "Trust Apple Development"
7. **לחץ "Trust" שוב** בחלון האישור

### שלב 3: הרץ שוב
1. חזור ל-Xcode
2. לחץ Run (▶️) שוב
3. האפליקציה תיפתח על ה-iPhone!

## הערות חשובות:

- **זה קורה רק בפעם הראשונה** - אחרי שתאשר, זה יעבוד תמיד
- **אם אין לך Apple Developer Account ($99/שנה)**, תוכל להריץ רק למשך 7 ימים
- **לאחר 7 ימים**, תצטרך להתקין מחדש או להירשם ל-Apple Developer Program

## אם אתה לא רואה "VPN & Device Management":

1. ודא שהאפליקציה הותקנה (אפילו אם לא נפתחה)
2. נסה לחפש "Device Management" או "Profiles"
3. אם עדיין לא מופיע, הרץ שוב ב-Xcode

## אם יש שגיאות ב-Xcode:

- ודא ש-Signing מוגדר נכון
- ודא שה-iPhone מחובר ונעול
- ודא שה-iPhone מאפשר "Trust This Computer"
