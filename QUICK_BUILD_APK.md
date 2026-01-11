# 🚀 בניית APK - הדרך הכי קלה

## ⚡ דרך מהירה: Android Studio (מומלץ!)

**לא צריך להתקין Java 21** - Android Studio משתמש ב-Java שלו!

### שלבים:

1. **פתח את הפרויקט:**
   ```bash
   npx cap open android
   ```

2. **בנה APK:**
   - **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - המתן לסיום הבנייה (יכול לקחת כמה דקות)

3. **מצא את ה-APK:**
   - לחץ על **"locate"** בהודעה שנפתחת
   - או: `android/app/build/outputs/apk/release/app-release.apk`

4. **העתק לשולחן העבודה:**
   ```bash
   VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
   cp android/app/build/outputs/apk/release/app-release.apk ~/Desktop/Family-Bank-${VERSION}.apk
   ```

## 🔄 דרך חלופית: Terminal (אם יש Java 21)

אם כבר התקנת Java 21:

```bash
./build_apk_with_java21.sh
```

## 📥 התקנת Java 21 (אם צריך)

אם רוצה לבנות דרך Terminal, צריך Java 21:

1. **הורד ידנית:**
   - פתח: https://adoptium.net/temurin/releases/?version=21
   - בחר: **macOS** / **aarch64** / **JDK 21** / **.pkg**
   - הורד והתקן

2. **בדוק:**
   ```bash
   /usr/libexec/java_home -V
   ```

3. **בנה:**
   ```bash
   ./build_apk_with_java21.sh
   ```

## ✅ סיכום

**הדרך הכי קלה:** דרך Android Studio - לא צריך כלום נוסף!
