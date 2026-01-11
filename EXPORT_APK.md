# 📦 ייצוא APK לפרודקשן

## איך לייצא APK שאפשר לשלוח לאנשים

### דרך 1: דרך Android Studio (מומלץ)

#### שלב 1: בחר Build Variant

1. **Build → Select Build Variant...**
   - בחר **prodRelease** (Production + Release)
   - לחץ **OK**

#### שלב 2: בנה APK

1. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - או: **Build → Generate Signed Bundle / APK...**
   - בחר **APK**
   - לחץ **Next**

2. **אם יש keystore:**
   - בחר **Use existing keystore**
   - בחר את `android/app/release.keystore`
   - הזן את הסיסמאות מ-`android/key.properties`
   - לחץ **Next**

3. **אם אין keystore:**
   - בחר **Create new keystore**
   - מלא את הפרטים
   - שמור את הסיסמאות!
   - לחץ **OK**

4. **Build Variants:**
   - בחר **prodRelease**
   - לחץ **Finish**

5. **המתן לסיום הבנייה**

#### שלב 3: מצא את ה-APK

לאחר הבנייה, תראה הודעה:
- **locate** - לחץ על זה
- או: `android/app/build/outputs/apk/prod/release/app-prod-release.apk`

### דרך 2: דרך Terminal (מהיר)

```bash
cd /Users/itzhakbachar/Projects/kids-money-manager

# בנה APK לפרודקשן
cd android
./gradlew assembleProdRelease
```

ה-APK יהיה ב:
```
android/app/build/outputs/apk/prod/release/app-prod-release.apk
```

### דרך 3: דרך Gradle Tasks

1. **View → Tool Windows → Gradle**
2. **Expand:** `android` → `app` → `Tasks` → `build`
3. **לחץ כפול** על `assembleProdRelease`
4. **לחץ כפול** על `assembleProdRelease` שוב (אם צריך)

ה-APK יהיה ב:
```
android/app/build/outputs/apk/prod/release/app-prod-release.apk
```

## בדיקה

לאחר הבנייה:

1. **מצא את ה-APK:**
   ```bash
   ls -lh android/app/build/outputs/apk/prod/release/
   ```

2. **בדוק את הגודל:**
   - אמור להיות בערך 5-10 MB

3. **בדוק את החתימה:**
   ```bash
   cd android
   ./gradlew signingReport
   ```
   - תחת `prodRelease`, אמור להיות כתוב "Config: release"

## שליחה לאנשים

### דרך 1: דרך Email/WhatsApp
1. **העתק את ה-APK:**
   ```bash
   cp android/app/build/outputs/apk/prod/release/app-prod-release.apk ~/Desktop/Family-Bank-3.11.11.apk
   ```

2. **שלח את הקובץ:**
   - דרך Email
   - דרך WhatsApp
   - דרך Google Drive / Dropbox

### דרך 2: דרך Google Drive
1. העלה את ה-APK ל-Google Drive
2. שתף את הקישור
3. אנשים יכולים להוריד ולהתקין

### דרך 3: דרך TestFlight / Google Play Internal Testing
- **iOS:** TestFlight (דורש Apple Developer Account)
- **Android:** Google Play Internal Testing (דורש Google Play Developer Account)

## התקנה על מכשיר

### Android:
1. **העבר את ה-APK למכשיר** (Email, USB, וכו')
2. **פתח את הקובץ במכשיר**
3. **אם יש אזהרה "Unknown source":**
   - Settings → Security → Allow installation from unknown sources
   - או: Settings → Apps → Special access → Install unknown apps
4. **לחץ Install**

## הערות חשובות

1. **Keystore:**
   - שמור את `android/app/release.keystore` במקום בטוח!
   - אם תאבד אותו, לא תוכל לעדכן את האפליקציה
   - שמור גם את הסיסמאות

2. **גרסה:**
   - כל פעם שמייצאים APK חדש, צריך להגדיל `versionCode`
   - זה כבר נעשה (versionCode 126)

3. **גודל:**
   - APK יכול להיות 5-10 MB
   - אם גדול מדי, אפשר להקטין עם ProGuard (אבל זה מורכב יותר)

4. **אבטחה:**
   - APK חתום = בטוח יותר
   - אנשים יכולים להתקין אותו בלי בעיות

## פתרון בעיות

### "Keystore not found"
**פתרון:**
```bash
cd /Users/itzhakbachar/Projects/kids-money-manager
./setup_android_build.sh
```

### "Build failed"
**פתרון:**
```bash
cd android
./gradlew clean
./gradlew assembleProdRelease
```

### "APK not signed"
**פתרון:**
- ודא ש-`android/key.properties` קיים
- ודא ש-`android/app/release.keystore` קיים
- ודא ש-`build.gradle` מכיל `signingConfig signingConfigs.release`

## סיכום מהיר

**הדרך הכי קלה:**
```bash
cd android
./gradlew assembleProdRelease
```

ה-APK יהיה ב:
```
android/app/build/outputs/apk/prod/release/app-prod-release.apk
```

**להעתקה לשולחן העבודה:**
```bash
cp android/app/build/outputs/apk/prod/release/app-prod-release.apk ~/Desktop/Family-Bank-3.11.11.apk
```
