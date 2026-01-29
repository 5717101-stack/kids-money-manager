# מדריך העלאה לגוגל פליי

## בניית AAB חתום

### 1. בדיקת הגדרות חתימה

וודא שקובץ `android/key.properties` קיים ומכיל:
```properties
storeFile=release.keystore
keyAlias=release
storePassword=android
keyPassword=android
```

וודא שקובץ `android/release.keystore` קיים.

### 2. בניית AAB חתום

```bash
cd android
./gradlew clean bundleProdRelease
```

הקובץ ייווצר ב:
```
android/app/build/outputs/bundle/prodRelease/app-prod-release.aab
```

### 3. העלאה לגוגל פליי

1. היכנס ל-[Google Play Console](https://play.google.com/console)
2. בחר את האפליקציה שלך
3. עבור ל-"Testing" > "Internal testing"
4. לחץ על "Create new release"
5. העלה את הקובץ: `android/app/build/outputs/bundle/prodRelease/app-prod-release.aab`

### 4. פתרון בעיות

**שגיאה: "All uploaded bundles must be signed"**

זה אומר שהקובץ לא חתום. פתרונות:

1. **וודא ש-`key.properties` קיים:**
   ```bash
   ls -la android/key.properties
   ```

2. **וודא ש-`release.keystore` קיים:**
   ```bash
   ls -la android/release.keystore
   ```

3. **בנה מחדש עם חתימה:**
   ```bash
   cd android
   ./gradlew clean bundleProdRelease
   ```

4. **אם עדיין לא עובד, בדוק את ה-path ב-`key.properties`:**
   - ה-path צריך להיות יחסית לתיקיית `android/`
   - אם ה-keystore נמצא ב-`android/release.keystore`, השתמש ב-`storeFile=release.keystore`
   - אם ה-keystore נמצא במקום אחר, עדכן את ה-path בהתאם

### 5. בדיקת חתימה

לאחר הבנייה, תוכל לבדוק שהקובץ חתום:

```bash
cd android
unzip -l app/build/outputs/bundle/prodRelease/app-prod-release.aab | grep -E "META-INF.*\.(RSA|DSA|EC|SF)"
```

אם אתה רואה קבצים כמו `META-INF/RELEASE.RSA` או `META-INF/RELEASE.SF`, הקובץ חתום.

### הערות חשובות

- **אל תעלה קבצים לא חתומים** - Google Play דורש חתימה
- **שמור את ה-keystore במקום בטוח** - אם תאבד אותו, לא תוכל לעדכן את האפליקציה
- **השתמש ב-`bundleProdRelease`** - זה בונה את ה-production release עם חתימה
