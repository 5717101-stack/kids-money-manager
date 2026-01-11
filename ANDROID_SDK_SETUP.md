# התקנת Android SDK

## בעיה
Android SDK לא מותקן. צריך להתקין אותו כדי לבנות APK.

## פתרון

### אופציה 1: התקנת Android Studio (מומלץ)
1. הורד Android Studio מ: https://developer.android.com/studio
2. התקן את Android Studio
3. פתח Android Studio
4. לך ל: **Tools → SDK Manager**
5. ודא שהתקנת:
   - ✅ Android SDK Platform-Tools
   - ✅ Android SDK Build-Tools
   - ✅ Android SDK Platform (גרסה 33 או מאוחר יותר)
6. לאחר ההתקנה, Android SDK יהיה ב: `~/Library/Android/sdk`

### אופציה 2: התקנת Command Line Tools בלבד
אם אתה לא רוצה להתקין את Android Studio המלא:

```bash
# צור תיקייה ל-SDK
mkdir -p ~/Library/Android/sdk

# הורד Command Line Tools
cd ~/Library/Android/sdk
curl -o cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip

# חלץ
unzip cmdline-tools.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true

# הגדר משתני סביבה
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools

# התקן SDK components
sdkmanager "platform-tools" "platforms;android-33" "build-tools;34.0.0"
```

## לאחר ההתקנה

1. הוסף ל-`~/.zshrc`:
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

2. טען מחדש:
```bash
source ~/.zshrc
```

3. צור את `android/local.properties`:
```bash
echo "sdk.dir=$HOME/Library/Android/sdk" > android/local.properties
```

4. הרץ שוב:
```bash
./build_apk.sh
```

## בדיקה
```bash
# בדוק אם SDK מותקן
ls -la ~/Library/Android/sdk

# בדוק אם ANDROID_HOME מוגדר
echo $ANDROID_HOME
```
