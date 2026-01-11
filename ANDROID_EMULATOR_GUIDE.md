# 🚀 מדריך להרצת האפליקציה על אמולטור אנדרואיד

## שלב 1: התקנת Android Studio

אם עדיין לא התקנת:
1. הורד Android Studio מ: https://developer.android.com/studio
2. התקן את Android Studio
3. פתח את Android Studio
4. ב-Android Studio → Settings → Appearance & Behavior → System Settings → Android SDK
5. ודא שהתקנת:
   - Android SDK Platform
   - Android SDK Build-Tools
   - Android Emulator

## שלב 2: יצירת אמולטור (Emulator)

### דרך 1: דרך Android Studio

1. **פתח Android Studio**
2. **Tools → Device Manager** (או לחץ על אייקון הטלפון בסרגל הכלים)
3. **Create Device** (לחץ על הכפתור)
4. **בחר מכשיר:**
   - בחר מכשיר (למשל: Pixel 5, Pixel 6)
   - לחץ **Next**
5. **בחר System Image:**
   - בחר גרסת Android (מומלץ: API 33 או 34)
   - אם אין, לחץ **Download** ליד הגרסה
   - לחץ **Next**
6. **Verify Configuration:**
   - בדוק את ההגדרות
   - לחץ **Finish**

### דרך 2: דרך Command Line

```bash
# פתח Android Studio SDK Manager
# או הרץ:
$ANDROID_HOME/emulator/emulator -list-avds

# אם אין אמולטורים, צור אחד:
# דרך Android Studio → Device Manager → Create Device
```

## שלב 3: פתיחת הפרויקט

```bash
cd /Users/itzhakbachar/Projects/kids-money-manager
npx cap open android
```

זה יפתח את Android Studio עם הפרויקט.

## שלב 4: הפעלת אמולטור

### דרך 1: דרך Android Studio

1. **ב-Android Studio:**
   - לחץ על **Device Manager** (אייקון הטלפון)
   - לחץ על **▶️ Play** ליד האמולטור שיצרת
   - האמולטור יפתח (זה יכול לקחת כמה דקות בפעם הראשונה)

2. **המתן שהאמולטור יטען:**
   - האמולטור יפתח חלון נפרד
   - המתן עד ש-Android יטען (כמה דקות בפעם הראשונה)

### דרך 2: דרך Command Line

```bash
# רשימת אמולטורים זמינים
$ANDROID_HOME/emulator/emulator -list-avds

# הפעלת אמולטור (החלף את השם בשם האמולטור שלך)
$ANDROID_HOME/emulator/emulator -avd Pixel_5_API_33
```

## שלב 5: הרצת האפליקציה

### דרך 1: דרך Android Studio

1. **ודא שהאמולטור רץ** (חלון נפרד פתוח)
2. **ב-Android Studio:**
   - בחר את האמולטור מהרשימה למעלה (ליד כפתור Run)
   - לחץ על **▶️ Run** (או Shift+F10)
   - או: **Run → Run 'app'**

3. **האפליקציה תתבנה ותותקן על האמולטור**

### דרך 2: דרך Command Line

```bash
# ודא שהאמולטור רץ
# ואז:
cd android
./gradlew installDebug

# או:
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## שלב 6: בדיקה

1. **באמולטור:**
   - האפליקציה תיפתח אוטומטית
   - או: חפש "Family Bank" ב-App Drawer

2. **בדוק את הגרסה:**
   - פתח את האפליקציה
   - לחץ על תפריט (☰)
   - בדוק את הגרסה בתחתית

## פתרון בעיות

### בעיה: "No emulators found"
**פתרון:**
1. פתח Android Studio
2. Tools → Device Manager
3. Create Device
4. צור אמולטור חדש

### בעיה: "SDK location not found"
**פתרון:**
```bash
# בדוק אם ANDROID_HOME מוגדר
echo $ANDROID_HOME

# אם לא, הגדר אותו:
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

### בעיה: "Emulator is slow"
**פתרון:**
1. הפעל Hardware Acceleration:
   - macOS: זה אמור לעבוד אוטומטית
   - Windows: הפעל HAXM דרך Android Studio
2. הגדל RAM של האמולטור:
   - Device Manager → Edit (עיפרון) → Advanced Settings → RAM

### בעיה: "Build failed"
**פתרון:**
```bash
# נקה build
cd android
./gradlew clean

# בנה מחדש
./gradlew build
```

## טיפים

1. **הפעל את האמולטור לפני הרצת האפליקציה** - זה חוסך זמן
2. **השתמש ב-Quick Boot** - האמולטור יטען מהר יותר
3. **שמור snapshot** - אחרי שהאמולטור טען, שמור snapshot (Device Manager → Edit → Snapshots)
4. **השתמש ב-Cold Boot** רק אם צריך - זה איטי יותר

## בדיקת חיבור

```bash
# בדוק אם האמולטור מחובר
adb devices

# אם רואה את המכשיר, הכל תקין
# אם לא, ודא שהאמולטור רץ
```

## סיכום מהיר

```bash
# 1. פתח Android Studio
npx cap open android

# 2. ב-Android Studio:
#    - Tools → Device Manager
#    - Create Device (אם אין)
#    - לחץ Play על האמולטור

# 3. לחץ Run (▶️) ב-Android Studio

# 4. האפליקציה תותקן ותפתח על האמולטור
```
