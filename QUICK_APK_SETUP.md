# הוראות מהירות לבניית APK

## שלב 1: התקנת Java (נדרש)

קובץ ההתקנה של Java כבר הורד. אם הוא נפתח אוטומטית:
1. לחץ "Continue" בחלון ההתקנה
2. לחץ "Install" 
3. הזן את סיסמת המנהל
4. המתן לסיום ההתקנה

אם החלון לא נפתח, הרץ:
```bash
open /tmp/openjdk.pkg
```

או הורד ידנית מ: https://adoptium.net/temurin/releases/?version=17

## שלב 2: התקנת Android SDK

1. הורד Android Studio מ: https://developer.android.com/studio
2. התקן את Android Studio
3. פתח Android Studio ולך ל: Tools → SDK Manager
4. ודא שהתקנת:
   - Android SDK Platform-Tools
   - Android SDK Build-Tools  
   - Android SDK Platform (גרסה 33+)

## שלב 3: הגדרת משתני סביבה

הוסף ל-`~/.zshrc`:
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

ואז הרץ:
```bash
source ~/.zshrc
```

## שלב 4: הרצת הסקריפטים

לאחר שהתקנת Java ו-Android SDK:

```bash
# הגדרת חתימה
./setup_android_build.sh

# בניית APK
./build_apk.sh
```

## פתרון בעיות

### Java לא נמצא אחרי התקנה
```bash
# בדוק אם Java מותקן
/usr/libexec/java_home -V

# אם כן, הגדר JAVA_HOME
export JAVA_HOME=$(/usr/libexec/java_home)
export PATH=$JAVA_HOME/bin:$PATH
```

### Android SDK לא נמצא
```bash
# בדוק אם Android SDK קיים
ls -la ~/Library/Android/sdk

# אם לא, התקן Android Studio והגדר ANDROID_HOME
export ANDROID_HOME=$HOME/Library/Android/sdk
```
