# 🚀 התקנה מהירה לאנדרואיד - הוראות שלב אחר שלב

## ✅ מה כבר הותקן:
- ✅ Android SDK Command Line Tools (ב-`~/Library/Android/sdk`)
- ✅ משתני סביבה הוגדרו ב-`~/.zshrc`
- ✅ `android/local.properties` נוצר

## 📋 מה צריך לעשות עכשיו:

### שלב 1: התקן Java (5 דקות)

**אפשרות א' - דרך Terminal (מהיר):**
```bash
# אם הקובץ קיים ב-/tmp/openjdk.pkg:
sudo installer -pkg /tmp/openjdk.pkg -target /

# או הורד חדש:
cd /Users/itzikbachar/Test\ Cursor
./install_java.sh
# ואז הרץ:
sudo installer -pkg /tmp/openjdk.pkg -target /
```

**אפשרות ב' - הורד ידנית (אם יש בעיה):**
1. לך ל: https://adoptium.net/temurin/releases/?version=17
2. בחר: **macOS** → **ARM64** (אם יש לך Mac עם Apple Silicon) או **x64** (אם יש לך Mac עם Intel)
3. הורד את הקובץ `.pkg`
4. לחץ פעמיים על הקובץ והתקן

**לאחר ההתקנה, בדוק:**
```bash
java -version
```
צריך לראות משהו כמו: `openjdk version "17.x.x"`

### שלב 2: טען משתני סביבה

פתח Terminal חדש או הרץ:
```bash
source ~/.zshrc
```

בדוק:
```bash
echo $ANDROID_HOME
# צריך להציג: /Users/itzikbachar/Library/Android/sdk
```

### שלב 3: התקן Android SDK Components

```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools

# קבל רישיונות
yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses

# התקן components
$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

זה יקח כמה דקות...

### שלב 4: הגדר חתימה

```bash
cd /Users/itzikbachar/Test\ Cursor
./setup_android_build.sh
```

### שלב 5: בנה APK

```bash
./build_apk.sh
```

ה-APK יהיה ב: `android/app/build/outputs/apk/release/app-release.apk`

---

## 🔍 בדיקה מהירה שהכל עובד:

```bash
# Java
java -version

# Android SDK
echo $ANDROID_HOME
ls $ANDROID_HOME/platform-tools/adb

# Gradle (בתיקיית android)
cd android
./gradlew --version
```

---

## ⚠️ בעיות נפוצות:

**Java לא נמצא אחרי התקנה:**
```bash
# בדוק אם Java מותקן
/usr/libexec/java_home -V

# הגדר JAVA_HOME
export JAVA_HOME=$(/usr/libexec/java_home)
export PATH=$JAVA_HOME/bin:$PATH
```

**Android SDK לא נמצא:**
```bash
# ודא ש-ANDROID_HOME מוגדר
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
```

**Gradle לא עובד:**
```bash
cd android
./gradlew clean
./gradlew --version
```

