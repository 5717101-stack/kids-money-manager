# תיקון תעודות פגות (Revoked Certificates)

## הבעיה
התעודות שלך פגו (revoked). זה קורה כש:
- התעודה פגה
- Apple ביטל את התעודה
- יש בעיה עם ה-Account

## פתרון מהיר

### שלב 1: מחק תעודות פגות

1. **פתח Xcode**
2. **Xcode → Settings** (או Preferences)
3. **Accounts tab**
4. **בחר את ה-Account שלך** (5717101@gmail.com)
5. **לחץ "Manage Certificates..."**
6. **מחק את כל התעודות הפגות** (יש X אדום לידן)
   - לחץ על התעודה
   - לחץ Delete או X
7. **לחץ "+" → "Apple Development"** ליצירת תעודה חדשה
8. **סגור את החלון**

### שלב 2: עדכן Signing ב-Project

1. **פתח את הפרויקט:**
   ```bash
   npx cap open ios
   ```

2. **בחר את הפרויקט:**
   - לחץ על "App" (הפרויקט הכחול)
   - בחר את ה-target "App" תחת TARGETS

3. **עבור ל-Signing & Capabilities:**
   - בחר את ה-tab "Signing & Capabilities"
   - ודא ש-"Automatically manage signing" מסומן ✅
   - בחר את ה-Team שלך מהרשימה

4. **אם יש שגיאות:**
   - לחץ "Try Again" או "Download Manual Profiles"
   - Xcode ייצור תעודה חדשה אוטומטית

### שלב 3: נקה ובנה מחדש

1. **Product → Clean Build Folder** (Shift+Cmd+K)
2. **Product → Build** (Cmd+B)
3. **Product → Run** (Cmd+R)

## אם עדיין לא עובד

### פתרון נוסף: מחק Provisioning Profiles

```bash
rm -rf ~/Library/MobileDevice/Provisioning\ Profiles/*
```

לאחר מכן:
1. פתח Xcode
2. Xcode → Settings → Accounts
3. בחר את ה-Account
4. לחץ "Download Manual Profiles"
5. חזור ל-Signing & Capabilities
6. בחר "Automatically manage signing" מחדש

### פתרון נוסף: מחק DerivedData

```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/App-*
```

לאחר מכן:
1. פתח Xcode מחדש
2. Product → Clean Build Folder
3. Product → Build

## בדיקה

לאחר התיקון, בדוק:
1. ✅ Signing & Capabilities → יש ✅ ירוק?
2. ✅ יש Provisioning Profile תקין?
3. ✅ המכשיר מופיע ב-Devices?

## הערות

- **Apple ID חינם:** יכול להריץ על מכשיר אחד למשך 7 ימים
- **Apple Developer Program ($99/שנה):** יכול להריץ על מכשירים רבים ול-TestFlight
- **תעודות:** Xcode יוצר תעודות חדשות אוטומטית אם "Automatically manage signing" מסומן
