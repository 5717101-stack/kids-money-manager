# 🔍 איך למצוא Build Variants ב-Android Studio

## אם Build Variants לא מופיע

### פתרון 1: פתח את ה-Panel ידנית

1. **ב-Android Studio:**
   - View → Tool Windows → Build Variants
   - או: לחץ על **Build Variants** בתחתית המסך (אם יש)
   - או: לחץ על **1: Project** בתחתית, ואז **Build Variants**

2. **אם עדיין לא מופיע:**
   - View → Tool Windows → **Build Variants** (Ctrl+Alt+B / Cmd+Option+B)

### פתרון 2: סנכרן Gradle

1. **File → Sync Project with Gradle Files**
   - או: לחץ על אייקון ה-Sync (🔄) בסרגל הכלים
   - או: Ctrl+Shift+O (Mac: Cmd+Shift+O)

2. **המתן לסיום הסינכרון**

3. **בדוק שוב:**
   - View → Tool Windows → Build Variants

### פתרון 3: בנה את הפרויקט

1. **Build → Clean Project**

2. **Build → Rebuild Project**

3. **המתן לסיום הבנייה**

4. **בדוק שוב:**
   - View → Tool Windows → Build Variants

### פתרון 4: בדוק את ה-Panel

1. **View → Tool Windows**
   - ודא ש-**Build Variants** מסומן (✓)
   - אם לא, לחץ עליו

2. **בדוק את התחתית:**
   - בתחתית המסך יש tabs: **1: Project**, **Build**, **Run**, וכו'
   - חפש **Build Variants** שם

### פתרון 5: דרך Run Configuration

אם Build Variants לא מופיע, אפשר לבחור variant דרך Run Configuration:

1. **לחץ על הרשימה הנפתחת ליד כפתור Run** (למעלה)
   - אמור להיות כתוב "app" או שם של configuration

2. **Edit Configurations...**

3. **אם יש Configuration קיימת:**
   - לחץ עליה
   - תחת **General** → **Build Variant**
   - בחר את ה-variant הרצוי

4. **אם אין Configuration:**
   - לחץ **+** (Add New Configuration)
   - בחר **Android App**
   - תחת **General** → **Build Variant**
   - בחר: `devDebug`, `prodDebug`, `devRelease`, או `prodRelease`

### פתרון 6: בדוק את build.gradle

אם עדיין לא עובד, בדוק שהקוד נטען:

1. **פתח:** `android/app/build.gradle`

2. **ודא שיש:**
   ```gradle
   buildTypes {
       debug { ... }
       release { ... }
   }
   
   flavorDimensions "environment"
   productFlavors {
       dev { ... }
       prod { ... }
   }
   ```

3. **אם אין, סנכרן Gradle שוב**

## דרך חלופית: דרך Gradle

אם Android Studio לא מציג, אפשר לבנות דרך Terminal:

```bash
cd android

# Dev Debug
./gradlew assembleDevDebug

# Prod Debug
./gradlew assembleProdDebug

# Prod Release
./gradlew assembleProdRelease
```

ואז להתקין:
```bash
# Dev Debug
adb install app/build/outputs/apk/dev/debug/app-dev-debug.apk

# Prod Debug
adb install app/build/outputs/apk/prod/debug/app-prod-debug.apk
```

## בדיקה מהירה

לאחר סינכרון Gradle, בדוק:

1. **Build → Select Build Variant...**
   - זה אמור להציג את כל ה-variants

2. **או דרך Terminal:**
   ```bash
   cd android
   ./gradlew tasks | grep -i variant
   ```

## אם כלום לא עובד

1. **סגור את Android Studio**

2. **מחק cache:**
   ```bash
   cd android
   ./gradlew clean
   rm -rf .gradle
   rm -rf app/build
   ```

3. **פתח מחדש:**
   ```bash
   npx cap open android
   ```

4. **File → Sync Project with Gradle Files**

5. **בדוק שוב:**
   - View → Tool Windows → Build Variants
