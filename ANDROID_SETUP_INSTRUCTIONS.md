# הוראות התקנה מהירות לאנדרואיד

## שלב 1: התקנת Java (נדרש סיסמת מנהל)

קובץ Java כבר הורד ל-`/tmp/openjdk.pkg`. 

**להתקנה:**
1. פתח Terminal והרץ:
   ```bash
   sudo installer -pkg /tmp/openjdk.pkg -target /
   ```
2. הזן את סיסמת המנהל
3. המתן לסיום ההתקנה

**או התקן ידנית:**
- הורד מ: https://adoptium.net/temurin/releases/?version=17
- בחר macOS ARM64 (אם יש לך Mac עם Apple Silicon) או x64 (אם יש לך Mac עם Intel)
- התקן את הקובץ שהורדת

**לאחר ההתקנה, בדוק:**
```bash
java -version
```

## שלב 2: Android SDK (הותקן אוטומטית)

Android SDK Command Line Tools הותקנו ב: `~/Library/Android/sdk`

**משתני הסביבה כבר הוגדרו ב-`~/.zshrc`**

**כדי לטעון אותם עכשיו:**
```bash
source ~/.zshrc
```

**או פתח Terminal חדש**

## שלב 3: הגדרת חתימה

לאחר ש-Java מותקן, הרץ:
```bash
cd /Users/itzikbachar/Test\ Cursor
./setup_android_build.sh
```

## שלב 4: בניית APK

```bash
./build_apk.sh
```

ה-APK יהיה ב: `android/app/build/outputs/apk/release/app-release.apk`

## בדיקה מהירה

```bash
# בדוק Java
java -version

# בדוק Android SDK
echo $ANDROID_HOME
ls $ANDROID_HOME/platform-tools/adb

# בדוק Gradle
cd android && ./gradlew --version
```

