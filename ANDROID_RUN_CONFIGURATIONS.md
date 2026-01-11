# ⚙️ הגדרת Run Configurations ב-Android Studio

## מה זה Run Configurations?

Run Configurations מאפשרות לך להגדיר איך האפליקציה תרוץ כשלוחצים Run:
- איזה build variant (debug/release)
- איזה device/emulator
- איזה environment (dev/prod)
- איזה launch options

## Build Variants שהוגדרו

### Debug Variants:
- **devDebug** - Development environment, debug build
- **prodDebug** - Production environment, debug build

### Release Variants:
- **devRelease** - Development environment, release build
- **prodRelease** - Production environment, release build (מומלץ לפרודקשן)

## איך להגדיר Run Configuration

### דרך 1: דרך Android Studio UI

1. **פתח Android Studio:**
   ```bash
   npx cap open android
   ```

2. **Edit Configurations:**
   - לחץ על הרשימה הנפתחת ליד כפתור Run (למעלה, ליד "app")
   - בחר **Edit Configurations...**

3. **צור Configuration חדשה:**
   - לחץ **+** (Add New Configuration)
   - בחר **Android App**

4. **הגדר את ה-Configuration:**
   - **Name:** למשל "Run Dev Debug" או "Run Prod Release"
   - **Module:** app
   - **Build Variant:** בחר את ה-variant הרצוי:
     - `devDebug` - לבדיקות
     - `prodDebug` - לבדיקות בפרודקשן
     - `devRelease` - לבדיקות release
     - `prodRelease` - לפרודקשן
   - **Launch:** 
     - **Default Activity** - יפתח את האפליקציה
     - **Nothing** - רק יתקין
   - **Target:** 
     - **USB Device** - מכשיר פיזי
     - **Emulator** - אמולטור ספציפי
     - **Show Device Chooser Dialog** - תמיד תשאל

5. **שמור:**
   - לחץ **OK**

### דרך 2: בחר Build Variant ישירות

1. **Build Variants Panel:**
   - View → Tool Windows → Build Variants
   - או: לחץ על **Build Variants** בתחתית המסך

2. **בחר Variant:**
   - תחת **Active Build Variant**, בחר:
     - `devDebug` - לבדיקות
     - `prodDebug` - לבדיקות בפרודקשן
     - `devRelease` - לבדיקות release
     - `prodRelease` - לפרודקשן

3. **הרץ:**
   - לחץ Run (▶️)
   - האפליקציה תרוץ עם ה-variant שנבחר

## דוגמאות ל-Run Configurations

### Configuration 1: Dev Debug (לפיתוח)
- **Name:** Dev Debug
- **Build Variant:** devDebug
- **Target:** Show Device Chooser Dialog
- **Launch:** Default Activity

### Configuration 2: Prod Debug (לבדיקות)
- **Name:** Prod Debug
- **Build Variant:** prodDebug
- **Target:** Show Device Chooser Dialog
- **Launch:** Default Activity

### Configuration 3: Prod Release (לפרודקשן)
- **Name:** Prod Release
- **Build Variant:** prodRelease
- **Target:** Show Device Chooser Dialog
- **Launch:** Default Activity

### Configuration 4: Dev Debug on Emulator (מהיר)
- **Name:** Dev Debug Emulator
- **Build Variant:** devDebug
- **Target:** [Emulator Name] (בחר אמולטור ספציפי)
- **Launch:** Default Activity

## שימוש ב-Run Configurations

1. **בחר Configuration:**
   - לחץ על הרשימה הנפתחת ליד כפתור Run
   - בחר את ה-Configuration הרצויה

2. **הרץ:**
   - לחץ Run (▶️) או Shift+F10
   - האפליקציה תרוץ עם ההגדרות שנבחרו

## Build Variants - הסבר

### Dev vs Prod:
- **Dev:** 
  - Application ID: `com.bachar.kidsmoneymanager.dev`
  - שם אפליקציה: "Family Bank Dev"
  - יכול לרוץ במקביל ל-Prod
  
- **Prod:**
  - Application ID: `com.bachar.kidsmoneymanager`
  - שם אפליקציה: "Family Bank"
  - זה הגרסה הסופית

### Debug vs Release:
- **Debug:**
  - Debuggable = true
  - לא חתום (או חתום עם debug key)
  - מהיר יותר לבנייה
  
- **Release:**
  - Debuggable = false
  - חתום עם release key
  - אופטימלי לפרודקשן

## טיפים

1. **שמור Configurations שונות:**
   - אחת לבדיקות (devDebug)
   - אחת לפרודקשן (prodRelease)

2. **השתמש ב-Quick Switch:**
   - Build Variants panel מאפשר החלפה מהירה
   - לא צריך ליצור Configuration לכל variant

3. **Device Selection:**
   - "Show Device Chooser Dialog" - תמיד תשאל
   - בחירת device ספציפי - מהיר יותר

4. **Launch Options:**
   - "Default Activity" - יפתח את האפליקציה אוטומטית
   - "Nothing" - רק יתקין, לא יפתח

## בדיקה

לאחר הגדרת Configuration:
1. בחר את ה-Configuration
2. לחץ Run
3. בדוק שהאפליקציה רצה עם ה-variant הנכון
4. בדוק את שם האפליקציה (Dev/Prod)

## פתרון בעיות

### "Build variant not found"
**פתרון:**
- Sync Project with Gradle Files (File → Sync Project with Gradle Files)
- או: Build → Clean Project, ואז Build → Rebuild Project

### "No device selected"
**פתרון:**
- ודא שיש device/emulator מחובר
- או: בחר "Show Device Chooser Dialog" ב-Target

### "Configuration not saved"
**פתרון:**
- ודא שלחצת OK אחרי יצירת Configuration
- בדוק ש-Android Studio לא נסגר לפני השמירה
