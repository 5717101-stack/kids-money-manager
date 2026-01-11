# 🔍 Build Variants ב-Android Studio Otter 2 (2025.2.2)

## מיקום Build Variants בגרסה החדשה

### דרך 1: דרך Toolbar (הכי מהיר)

1. **בסרגל הכלים העליון:**
   - חפש את הרשימה הנפתחת ליד כפתור **Run** (▶️)
   - אמור להיות כתוב "app" או שם של configuration
   - **לחץ עליו** → **Edit Configurations...**

2. **ב-Edit Configurations:**
   - אם יש configuration קיימת, לחץ עליה
   - תחת **General** → **Build Variant**
   - בחר: `devDebug`, `prodDebug`, `devRelease`, או `prodRelease`

### דרך 2: דרך Build Menu

1. **Build → Select Build Variant...**
   - זה יפתח חלון עם כל ה-variants הזמינים

### דרך 3: דרך Project Structure

1. **File → Project Structure** (או Cmd+;)
2. **Modules** → **app**
3. **Flavors** tab
4. שם תראה את כל ה-flavors (dev, prod)
5. **Build Types** tab
6. שם תראה את כל ה-build types (debug, release)

### דרך 4: דרך Gradle Panel

1. **View → Tool Windows → Gradle**
2. **Expand:** `android` → `app` → `Tasks` → `build`
3. שם תראה tasks כמו:
   - `assembleDevDebug`
   - `assembleProdDebug`
   - `assembleDevRelease`
   - `assembleProdRelease`
4. **לחיצה כפולה** על task תבנה את ה-variant

### דרך 5: דרך Run Configuration (מומלץ)

1. **לחץ על הרשימה הנפתחת ליד Run** (למעלה)
   - אמור להיות כתוב "app" או שם של configuration

2. **אם יש "app":**
   - זה כבר configuration ברירת מחדש
   - לחץ עליו → **Edit Configurations...**
   - תחת **General** → **Build Variant**
   - בחר את ה-variant הרצוי

3. **אם אין:**
   - לחץ **Edit Configurations...**
   - לחץ **+** → **Android App**
   - **Name:** למשל "Dev Debug"
   - **Module:** app
   - **Build Variant:** בחר `devDebug`
   - **Target:** Show Device Chooser Dialog
   - **Launch:** Default Activity
   - לחץ **OK**

## איך להשתמש

### שיטה 1: דרך Run Configuration (מומלץ)

1. **לחץ על הרשימה ליד Run** → **Edit Configurations...**
2. **בחר או צור Configuration**
3. **תחת Build Variant**, בחר:
   - `devDebug` - לפיתוח
   - `prodDebug` - לבדיקות
   - `prodRelease` - לפרודקשן
4. **לחץ OK**
5. **לחץ Run** (▶️)

### שיטה 2: דרך Build Menu

1. **Build → Select Build Variant...**
2. **בחר variant** מהרשימה
3. **לחץ OK**
4. **לחץ Run** (▶️)

### שיטה 3: דרך Gradle Tasks

1. **View → Tool Windows → Gradle**
2. **Expand:** `android` → `app` → `Tasks` → `build`
3. **לחץ כפול** על:
   - `assembleDevDebug` - לבנייה
   - `installDevDebug` - לבנייה והתקנה

## אם עדיין לא מופיע

### פתרון 1: סנכרן Gradle

1. **File → Sync Project with Gradle Files**
   - או: לחץ על אייקון **Sync** (🔄) בסרגל הכלים
   - או: **Cmd+Shift+O**

2. **המתן לסיום הסינכרון**

### פתרון 2: נקה ובנה מחדש

1. **Build → Clean Project**
2. **Build → Rebuild Project**
3. **File → Sync Project with Gradle Files**

### פתרון 3: בדוק את build.gradle

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

## דרך Terminal (אם Android Studio לא עובד)

```bash
cd android

# Dev Debug
./gradlew assembleDevDebug
adb install app/build/outputs/apk/dev/debug/app-dev-debug.apk

# Prod Debug
./gradlew assembleProdDebug
adb install app/build/outputs/apk/prod/debug/app-prod-debug.apk

# Prod Release
./gradlew assembleProdRelease
adb install app/build/outputs/apk/prod/release/app-prod-release.apk
```

## טיפים

1. **השתמש ב-Run Configuration:**
   - זה הכי נוח בגרסה החדשה
   - אפשר לשמור כמה configurations שונות

2. **Build → Select Build Variant:**
   - מהיר להחלפה בין variants
   - משפיע על כל ה-builds

3. **Gradle Panel:**
   - טוב לראות את כל ה-tasks
   - טוב לבנייה ידנית

## סיכום מהיר

**הדרך הכי קלה:**
1. לחץ על הרשימה ליד Run → **Edit Configurations...**
2. תחת **Build Variant**, בחר את ה-variant
3. לחץ **OK**
4. לחץ **Run**

**או:**
1. **Build → Select Build Variant...**
2. בחר variant
3. לחץ **OK**
4. לחץ **Run**
