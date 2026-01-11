# תיקון שגיאת חתימה ב-iOS

## הבעיה
```
The executable is ad-hoc signed, which is not supported on this device.
The identity used to sign the executable is no longer valid.
```

## פתרונות

### פתרון 1: הגדרת Signing ב-Xcode (מומלץ)

1. **פתח את Xcode:**
   ```bash
   npx cap open ios
   ```

2. **בחר את הפרויקט:**
   - לחץ על "App" ב-navigator (הפרויקט הכחול)
   - בחר את ה-target "App" תחת TARGETS

3. **עבור ל-Signing & Capabilities:**
   - בחר את ה-tab "Signing & Capabilities"
   - ודא ש-"Automatically manage signing" מסומן ✅

4. **בחר Team:**
   - בחר את ה-Team שלך מהרשימה
   - אם אין Team, לחץ "Add Account..." והוסף את Apple ID שלך

5. **בדוק Bundle Identifier:**
   - ודא שה-Bundle Identifier ייחודי (למשל: `com.bachar.kidsmoneymanager`)
   - אם יש קונפליקט, שנה אותו למשהו ייחודי

6. **נקה Build:**
   - Product → Clean Build Folder (Shift+Cmd+K)

7. **בנה מחדש:**
   - Product → Build (Cmd+B)
   - Product → Run (Cmd+R)

### פתרון 2: אם יש בעיה עם Provisioning Profile

1. **מחק Provisioning Profiles ישנים:**
   ```bash
   rm -rf ~/Library/MobileDevice/Provisioning\ Profiles/*
   ```

2. **ב-Xcode:**
   - Xcode → Settings → Accounts
   - בחר את ה-Account שלך
   - לחץ "Download Manual Profiles"
   - חזור ל-Signing & Capabilities
   - בחר "Automatically manage signing" מחדש

### פתרון 3: אם המכשיר לא רשום

1. **ב-Xcode:**
   - Window → Devices and Simulators
   - בחר את המכשיר שלך
   - ודא שהוא מופיע כ-"Connected"
   - אם יש אזהרה, לחץ "Use for Development"

2. **במכשיר:**
   - Settings → General → VPN & Device Management
   - ודא שהמפתח שלך מאושר

### פתרון 4: אם התעודה פגה

1. **בדוק תעודות:**
   ```bash
   security find-identity -v -p codesigning
   ```

2. **ב-Xcode:**
   - Xcode → Settings → Accounts
   - בחר את ה-Account
   - לחץ "Manage Certificates"
   - אם יש תעודה פגה, מחק אותה
   - לחץ "+" ליצירת תעודה חדשה

### פתרון 5: אם כלום לא עובד

1. **מחק DerivedData:**
   ```bash
   rm -rf ~/Library/Developer/Xcode/DerivedData/App-*
   ```

2. **מחק Pods ו-CocoaPods cache:**
   ```bash
   cd ios/App
   rm -rf Pods Podfile.lock
   pod install
   ```

3. **סנכרן Capacitor מחדש:**
   ```bash
   cd ../..
   npm run build
   npx cap sync ios
   ```

4. **פתח Xcode מחדש:**
   ```bash
   npx cap open ios
   ```

5. **נקה ובנה:**
   - Product → Clean Build Folder
   - Product → Build

## בדיקה מהירה

לאחר התיקון, בדוק:
1. ב-Xcode → Signing & Capabilities → האם יש ✅ ירוק?
2. האם יש Provisioning Profile תקין?
3. האם המכשיר מופיע ב-Devices?

## הערות חשובות

- **Apple Developer Account:** צריך Apple ID (חינם) או Apple Developer Program ($99/שנה)
- **Bundle ID:** חייב להיות ייחודי - אם כבר קיים, שנה אותו
- **Device:** המכשיר צריך להיות רשום ב-Apple ID שלך

## אם עדיין לא עובד

1. בדוק את ה-console ב-Xcode לראות שגיאות נוספות
2. ודא שהמכשיר מחובר ו-unlocked
3. נסה להריץ על סימולטור קודם (לבדיקה)
4. בדוק אם יש עדכונים ל-Xcode
