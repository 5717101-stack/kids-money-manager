# ✅ APK לאנדרואיד מוכן!

## 📱 מיקום ה-APK:

ה-APK החתום נמצא ב:
- **`android/app/build/outputs/apk/release/app-release.apk`**
- **גם בעותק עם timestamp בשורש הפרויקט:** `Family-Bank-Release-YYYYMMDD-HHMMSS.apk`

## ✅ מה הותקן:

1. ✅ **Java JDK 17** - מותקן
2. ✅ **Android SDK Command Line Tools** - מותקן ב-`~/Library/Android/sdk`
3. ✅ **Android SDK Components:**
   - Platform Tools
   - Android SDK Platform 34
   - Build Tools 34.0.0
4. ✅ **Keystore** - נוצר ב-`android/app/release.keystore`
5. ✅ **APK חתום** - מוכן להתקנה

## 📊 פרטי ה-APK:

- **גרסה:** 3.10.13
- **Version Code:** 123
- **Package ID:** com.bachar.kidsmoneymanager
- **גודל:** ~3.3 MB

## 🚀 התקנה על מכשיר:

### דרך 1: USB Debugging
1. הפעל USB Debugging במכשיר (Settings → Developer Options)
2. חבר את המכשיר למחשב
3. הרץ:
   ```bash
   adb install android/app/build/outputs/apk/release/app-release.apk
   ```

### דרך 2: העברה ידנית
1. העבר את ה-APK למכשיר (דרך email, cloud, וכו')
2. פתח את הקובץ במכשיר
3. אפשר התקנה מ-"Unknown Sources" אם נדרש
4. התקן

## 📝 הערות חשובות:

1. **Keystore:** שמור את `android/app/release.keystore` במקום בטוח! בלי זה לא תוכל לעדכן את האפליקציה.
2. **סיסמאות:** הסיסמאות הדיפולטיות הן `android` - שנה אותן ב-`android/key.properties` לפני שחרור לפרודקשן.
3. **Version Code:** לפני כל שחרור חדש, עדכן את `versionCode` ב-`android/app/build.gradle` (חייב להיות גדול מהגרסה הקודמת).

## 🔄 בניית APK חדש:

```bash
./build_apk.sh
```

או ידנית:
```bash
npm run build
npx cap sync android
cd android
./gradlew assembleRelease
```

## 📦 שחרור ל-Google Play:

לפני העלאה ל-Google Play, בנה AAB (Android App Bundle):
```bash
cd android
./gradlew bundleRelease
```

ה-AAB יהיה ב: `app/build/outputs/bundle/release/app-release.aab`

