# בניית APK לאנדרואיד

מדריך לבניית APK חתום לאנדרואיד.

## דרישות מוקדמות

### 1. התקנת Java JDK
- הורד Java JDK 17 או מאוחר יותר מ: https://adoptium.net/
- או התקן דרך Homebrew: `brew install --cask temurin`
- ודא ש-Java מותקן: `java -version`

### 2. התקנת Android SDK
- הורד והתקן Android Studio מ: https://developer.android.com/studio
- לאחר ההתקנה, הגדר משתני סביבה:

```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

הוסף את השורות האלה ל-`~/.zshrc` או `~/.bash_profile` כדי שיפעלו תמיד.

### 3. התקנת Android SDK Components
פתח Android Studio ולך ל:
- Tools → SDK Manager
- ודא שהתקנת:
  - Android SDK Platform-Tools
  - Android SDK Build-Tools
  - Android SDK Platform (גרסה 33 או מאוחר יותר)

## הגדרת חתימה (Signing)

### אוטומטי (מומלץ)
הרץ את הסקריפט:
```bash
./setup_android_build.sh
```

הסקריפט ייצור:
- `android/app/release.keystore` - קובץ החתימה
- `android/key.properties` - קובץ הגדרות עם סיסמאות

**⚠️ חשוב:** 
- שמור את `release.keystore` במקום בטוח!
- שנה את הסיסמאות ב-`android/key.properties` לפני שחרור לפרודקשן
- הוסף `android/key.properties` ל-`.gitignore` (כבר קיים)

### ידני
אם אתה רוצה ליצור keystore ידנית:

```bash
keytool -genkey -v -keystore android/app/release.keystore \
    -alias release -keyalg RSA -keysize 2048 -validity 10000
```

ואז צור `android/key.properties`:
```properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=release
storeFile=release.keystore
```

## בניית APK

### שיטה 1: סקריפט אוטומטי (מומלץ)
```bash
./build_apk.sh
```

הסקריפט:
1. בונה את הנכסים של ה-web
2. מסנכרן את Capacitor
3. בונה את ה-APK החתום
4. מעתיק את ה-APK לשורש הפרויקט עם timestamp

### שיטה 2: ידני

1. בנה את הנכסים:
```bash
npm run build
```

2. סנכרן Capacitor:
```bash
npx cap sync android
```

3. בנה APK:
```bash
cd android
./gradlew assembleRelease
```

ה-APK יהיה ב: `android/app/build/outputs/apk/release/app-release.apk`

## מיקום ה-APK

לאחר הבנייה, ה-APK יהיה ב:
- `android/app/build/outputs/apk/release/app-release.apk`
- גם בעותק עם timestamp בשורש הפרויקט

## פתרון בעיות

### שגיאת Java לא נמצא
```bash
# בדוק אם Java מותקן
java -version

# אם לא, התקן Java JDK 17+
```

### שגיאת ANDROID_HOME לא מוגדר
```bash
# הוסף ל-~/.zshrc או ~/.bash_profile
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools

# טען מחדש
source ~/.zshrc
```

### שגיאת Gradle
```bash
cd android
./gradlew clean
./gradlew assembleRelease
```

### APK לא חתום
ודא ש:
- `android/key.properties` קיים
- `android/app/release.keystore` קיים
- הסיסמאות ב-`key.properties` נכונות

## הערות חשובות

1. **גיבוי Keystore**: שמור את `release.keystore` במקום בטוח! בלי זה לא תוכל לעדכן את האפליקציה בחנות.
2. **סיסמאות**: שנה את הסיסמאות הדיפולטיות לפני שחרור לפרודקשן.
3. **גרסה**: עדכן `versionCode` ו-`versionName` ב-`android/app/build.gradle` לפני כל שחרור.
4. **בדיקה**: בדוק את ה-APK על מכשיר אמיתי לפני שחרור.

## שחרור ל-Google Play

לפני העלאה ל-Google Play:
1. ודא שה-APK חתום
2. בדוק את הגרסה (`versionCode` חייב להיות גדול מהגרסה הקודמת)
3. צור AAB (Android App Bundle) במקום APK:
   ```bash
   cd android
   ./gradlew bundleRelease
   ```
   ה-AAB יהיה ב: `app/build/outputs/bundle/release/app-release.aab`
