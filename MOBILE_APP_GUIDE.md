# מדריך להפיכת האפליקציה לאפליקציית iOS/Android

## סקירה כללית

אנחנו נשתמש ב-**Capacitor** - כלי שמאפשר לעטוף את האפליקציה הקיימת (React + Vite) ולהפוך אותה לאפליקציית native בלי לכתוב מחדש את כל הקוד.

### יתרונות:
- ✅ משתמשים ברוב הקוד הקיים
- ✅ תמיכה ב-iOS ו-Android
- ✅ גישה ל-APIs של המכשיר (Camera, Storage, וכו')
- ✅ הפצה דרך App Store ו-Google Play

---

## דרישות מוקדמות

### 1. macOS (חובה ל-iOS)
- Mac עם macOS 10.15 או חדש יותר
- Xcode (מ-App Store, ~12GB)
- CocoaPods: `sudo gem install cocoapods`

### 2. Android (יכול להיות על Windows/Mac/Linux)
- Android Studio
- Java Development Kit (JDK) 11 או חדש יותר

### 3. חשבונות מפתחים
- **Apple Developer Account**: $99/שנה (חובה ל-iOS)
- **Google Play Console**: $25 חד-פעמי (חובה ל-Android)

---

## שלב 1: התקנת Capacitor

```bash
cd "/Users/itzikbachar/Test Cursor"

# התקן Capacitor
npm install @capacitor/core @capacitor/cli

# התקן פלטפורמות
npm install @capacitor/ios @capacitor/android

# התקן פלאגינים נחוצים
npm install @capacitor/app @capacitor/keyboard @capacitor/status-bar
```

---

## שלב 2: הגדרת Capacitor

### 2.1 אתחול Capacitor

```bash
npx cap init
```

תשאל אותך שאלות:
- **App name**: `Kids Money Manager`
- **App ID**: `com.yourname.kidsmoneymanager` (השתמש ב-reverse domain notation)
- **Web dir**: `dist`

### 2.2 עדכון `package.json`

הוסף סקריפטים חדשים:

```json
{
  "scripts": {
    "build": "vite build",
    "build:mobile": "vite build && npx cap sync",
    "ios": "npx cap open ios",
    "android": "npx cap open android"
  }
}
```

### 2.3 עדכון `vite.config.js`

וודא שהבסיס URL נכון:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './', // חשוב למובייל!
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
```

---

## שלב 3: הוספת פלטפורמות

### 3.1 בניית האפליקציה

```bash
npm run build
```

### 3.2 סינכרון עם Capacitor

```bash
npx cap sync
```

זה ייצור תיקיות:
- `ios/` - פרויקט Xcode
- `android/` - פרויקט Android Studio

---

## שלב 4: הגדרת iOS

### 4.1 פתיחת פרויקט ב-Xcode

```bash
npx cap open ios
```

או:
```bash
open ios/App/App.xcworkspace
```

### 4.2 הגדרת Signing & Capabilities

1. ב-Xcode, בחר את הפרויקט (App) בתפריט השמאלי
2. בחר את ה-Target "App"
3. לחץ על **"Signing & Capabilities"**
4. סמן **"Automatically manage signing"**
5. בחר את **Team** שלך (Apple Developer Account)

### 4.3 עדכון Bundle Identifier

1. ב-**General** → **Identity**
2. שנה את **Bundle Identifier** ל: `com.yourname.kidsmoneymanager`
3. ודא שזה תואם ל-App ID שהגדרת ב-Capacitor

### 4.4 הגדרת Info.plist

פתח `ios/App/App/Info.plist` והוסף:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

(זה מאפשר חיבורים ל-API שלך)

### 4.5 עדכון API URL

פתח `src/utils/api.js` והוסף לוגיקה לזיהוי סביבה:

```javascript
const getApiUrl = () => {
  // אם אנחנו באפליקציית מובייל
  if (window.Capacitor) {
    // השתמש ב-API הייצור שלך
    return 'https://your-railway-app.up.railway.app/api';
  }
  // אחרת, השתמש במשתנה סביבה
  return import.meta.env.VITE_API_URL || 'http://localhost:3001/api';
};

const API_URL = getApiUrl();
```

---

## שלב 5: בנייה והפצה ל-iOS

### 5.1 בנייה ל-Simulator (לבדיקה)

1. ב-Xcode, בחר **Simulator** (iPhone 14 Pro, וכו')
2. לחץ **▶️ Run** (Cmd+R)
3. האפליקציה תיפתח ב-Simulator

### 5.2 בנייה ל-Device (לבדיקה אמיתית)

1. חבר iPhone למחשב
2. ב-Xcode, בחר את המכשיר שלך
3. לחץ **▶️ Run**
4. ב-iPhone: Settings → General → VPN & Device Management → Trust Developer

### 5.3 בנייה ל-TestFlight (הפצה למשתמשים ספציפיים)

#### א. יצירת Archive

1. ב-Xcode: **Product** → **Archive**
2. המתן לסיום הבנייה
3. יפתח **Organizer**

#### ב. העלאה ל-App Store Connect

1. ב-Organizer, בחר את ה-Archive
2. לחץ **"Distribute App"**
3. בחר **"App Store Connect"**
4. לחץ **"Next"** → **"Upload"**
5. המתן להעלאה (10-15 דקות)

#### ג. הגדרת TestFlight

1. היכנס ל-[App Store Connect](https://appstoreconnect.apple.com)
2. בחר את האפליקציה שלך
3. לחץ **"TestFlight"** בתפריט
4. לחץ **"Internal Testing"** או **"External Testing"**
5. הוסף משתמשים (על ידי Apple ID שלהם)
6. לחץ **"Submit for Review"** (אם External)

#### ד. משתמשים מקבלים הודעה

- משתמשים יקבלו אימייל מ-Apple
- הם יצטרכו להתקין את **TestFlight** מה-App Store
- הם יוכלו להוריד את האפליקציה דרך TestFlight

---

## שלב 6: הגדרת Android

### 6.1 פתיחת פרויקט ב-Android Studio

```bash
npx cap open android
```

או:
```bash
# פתח Android Studio
# File → Open → בחר תיקיית android/
```

### 6.2 עדכון API URL

פתח `android/app/src/main/assets/public/index.html` (אם קיים) או עדכן ב-`src/utils/api.js` כמו ב-iOS.

### 6.3 עדכון AndroidManifest.xml

פתח `android/app/src/main/AndroidManifest.xml` והוסף:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application
    android:usesCleartextTraffic="true"
    ...>
```

### 6.4 עדכון build.gradle

פתח `android/app/build.gradle`:

```gradle
android {
    compileSdkVersion 34
    
    defaultConfig {
        minSdkVersion 22
        targetSdkVersion 34
        ...
    }
}
```

---

## שלב 7: בנייה והפצה ל-Android

### 7.1 בנייה ל-Emulator (לבדיקה)

1. ב-Android Studio, לחץ **▶️ Run**
2. בחר Emulator או מכשיר מחובר
3. האפליקציה תותקן ותפתח

### 7.2 בנייה ל-APK (לבדיקה)

```bash
cd android
./gradlew assembleDebug
```

ה-APK יהיה ב: `android/app/build/outputs/apk/debug/app-debug.apk`

### 7.3 בנייה ל-AAB (להפצה)

```bash
cd android
./gradlew bundleRelease
```

ה-AAB יהיה ב: `android/app/build/outputs/bundle/release/app-release.aab`

### 7.4 העלאה ל-Google Play Console

1. היכנס ל-[Google Play Console](https://play.google.com/console)
2. צור אפליקציה חדשה
3. **"Production"** → **"Create new release"**
4. העלה את ה-AAB
5. **"Internal testing"** → הוסף משתמשים (על ידי Gmail)
6. לחץ **"Review release"**

---

## שלב 8: עדכונים עתידיים

### תהליך עדכון:

1. **עדכן את הקוד** (כמו תמיד)
2. **בנה מחדש:**
   ```bash
   npm run build
   npx cap sync
   ```
3. **עדכן ב-Xcode/Android Studio:**
   - iOS: Product → Archive → Upload
   - Android: Build → Generate Signed Bundle → Upload

---

## פתרון בעיות נפוצות

### iOS: "No signing certificate found"
- פתרון: היכנס ל-[Apple Developer](https://developer.apple.com) → Certificates → צור חדש

### iOS: "App Transport Security"
- פתח `Info.plist` והוסף את ההגדרות שצוינו למעלה

### Android: "Gradle sync failed"
- פתח Android Studio → File → Invalidate Caches → Restart

### Android: "INSTALL_FAILED_INSUFFICIENT_STORAGE"
- מחק אפליקציות ישנות מהמכשיר

### API לא עובד במובייל
- ודא שה-API URL נכון
- ודא שה-API מאפשר CORS
- בדוק את ה-Logs ב-Xcode/Android Studio

---

## משתני סביבה למובייל

### עדכון `src/utils/api.js`:

```javascript
const getApiUrl = () => {
  // Production API
  const PRODUCTION_API = 'https://your-railway-app.up.railway.app/api';
  
  // אם אנחנו באפליקציית מובייל
  if (window.Capacitor?.isNativePlatform()) {
    return PRODUCTION_API;
  }
  
  // אחרת, השתמש במשתנה סביבה (לפיתוח)
  return import.meta.env.VITE_API_URL || 'http://localhost:3001/api';
};

export const API_URL = getApiUrl();
```

---

## עלויות

### iOS:
- **Apple Developer Program**: $99/שנה
- **TestFlight**: חינם (עד 10,000 משתמשים)

### Android:
- **Google Play Console**: $25 חד-פעמי
- **Internal Testing**: חינם

---

## סיכום

1. ✅ התקן Capacitor
2. ✅ הוסף פלטפורמות (iOS/Android)
3. ✅ עדכן API URLs
4. ✅ בנה והעלה ל-TestFlight/Google Play
5. ✅ הוסף משתמשים לבדיקה

**זמן משוער**: 2-4 שעות להגדרה ראשונית

**לעזרה נוספת**: [Capacitor Docs](https://capacitorjs.com/docs)

