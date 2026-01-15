# 🔧 תיקון בעיות Signing ב-Xcode - מדריך מהיר

## הבעיות שמוצגות:
1. ❌ "No Accounts: Add a new account in Accounts settings"
2. ❌ "No profiles for 'com.bachar.kidsmoneymanager.testing' were found"

## פתרון שלב אחר שלב:

### שלב 1: הוסף Apple ID ב-Xcode

1. **פתח Xcode Settings:**
   - Xcode → Settings (או Preferences - Cmd+,)
   - בחר את ה-tab **"Accounts"**

2. **הוסף Apple ID:**
   - לחץ על כפתור **"+"** (בפינה השמאלית התחתונה)
   - בחר **"Apple ID"**
   - היכנס עם Apple ID שלך (אימייל וסיסמה)
   - לחץ **"Sign In"**

3. **אם יש שגיאה:**
   - ודא שיש לך חיבור לאינטרנט
   - נסה שוב
   - אם יש Two-Factor Authentication, הזן את הקוד

### שלב 2: הגדר Signing & Capabilities

1. **בחר את הפרויקט:**
   - ב-Xcode, לחץ על **"App"** (הפרויקט הכחול בצד שמאל)
   - תחת **TARGETS**, בחר **"App"**

2. **עבור ל-Signing & Capabilities:**
   - בחר את ה-tab **"Signing & Capabilities"** (בחלק העליון)

3. **הגדר Signing:**
   - ✅ סמן **"Automatically manage signing"**
   - תחת **"Team"**, בחר את ה-Team שלך מהרשימה
   - אם אין Team, לחץ **"Add Account..."** והוסף את Apple ID

4. **בדוק Bundle Identifier:**
   - ודא ש-Bundle Identifier הוא: `com.bachar.kidsmoneymanager` (ללא .testing)
   - אם יש `.testing`, שנה אותו ל-`com.bachar.kidsmoneymanager`

### שלב 3: נקה ובנה מחדש

1. **נקה Build:**
   - Product → Clean Build Folder (Shift+Cmd+K)

2. **בנה מחדש:**
   - Product → Build (Cmd+B)
   - בדוק שאין שגיאות

3. **הרץ:**
   - בחר Simulator (iPhone 15 Pro, iPhone 16 Pro, וכו')
   - Product → Run (Cmd+R)

## אם עדיין יש בעיות:

### פתרון נוסף: מחק Provisioning Profiles ישנים

```bash
rm -rf ~/Library/MobileDevice/Provisioning\ Profiles/*
```

לאחר מכן:
1. חזור ל-Xcode
2. Xcode → Settings → Accounts
3. בחר את ה-Account שלך
4. לחץ **"Download Manual Profiles"**
5. חזור ל-Signing & Capabilities
6. בחר **"Automatically manage signing"** מחדש

### פתרון נוסף: מחק DerivedData

```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/App-*
```

לאחר מכן:
1. סגור את Xcode
2. פתח מחדש: `npx cap open ios`
3. Product → Clean Build Folder
4. Product → Build

## הערות חשובות:

- **ללא Apple Developer Account ($99/שנה):** תוכל להריץ רק על Simulator
- **עם Apple Developer Account:** תוכל להריץ על מכשיר אמיתי ולהפיץ ל-TestFlight
- **Bundle Identifier:** חייב להיות ייחודי. אם יש קונפליקט, שנה אותו למשהו אחר

## בדיקה מהירה:

לאחר שסיימת, בדוק:
- ✅ יש Team נבחר (לא "None")
- ✅ "Automatically manage signing" מסומן
- ✅ אין שגיאות אדומות ב-Signing & Capabilities
- ✅ Run button פעיל (לא אפור)

---

**אם עדיין יש בעיות, שלח לי את השגיאות המדויקות מ-Xcode.**
