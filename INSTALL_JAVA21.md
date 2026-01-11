# ☕ התקנת Java 21 לבניית APK

## הבעיה

Capacitor דורש Java 21 לבניית APK, אבל יש רק Java 17 מותקן.

## ✅ Java 21 הורד!

הקובץ נמצא ב: `/tmp/openjdk21.pkg`

## 📦 התקנה

### שלב 1: התקן Java 21

**אם החלון נפתח אוטומטית:**
1. לחץ **Continue**
2. הזן את **סיסמת המנהל**
3. לחץ **Install**
4. המתן לסיום ההתקנה

**אם החלון לא נפתח:**
```bash
open /tmp/openjdk21.pkg
```

### שלב 2: בדוק שהתקנה

```bash
/usr/libexec/java_home -V
```

אמור להציג גם Java 21:
```
21.x.x (arm64) "Eclipse Adoptium" - "OpenJDK 21.x.x" /Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home
```

### שלב 3: עדכן את gradle.properties

```bash
cd /Users/itzhakbachar/Projects/kids-money-manager
```

ערוך את `android/gradle.properties`:
```properties
org.gradle.java.home=/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home
```

### שלב 4: בנה APK

```bash
cd android
./gradlew --stop
./gradlew clean
./gradlew assembleRelease
```

## 🎉 לאחר הבנייה

ה-APK יהיה ב:
```
android/app/build/outputs/apk/release/app-release.apk
```

**להעתקה לשולחן העבודה:**
```bash
VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
cp android/app/build/outputs/apk/release/app-release.apk ~/Desktop/Family-Bank-${VERSION}.apk
```

## 🔄 דרך חלופית: Android Studio

אם לא רוצה להתקין Java 21, אפשר לבנות דרך Android Studio:

1. **פתח את הפרויקט:**
   ```bash
   npx cap open android
   ```

2. **בנה APK:**
   - **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - המתן לסיום הבנייה

3. **מצא את ה-APK:**
   - לחץ על "locate" בהודעה
   - או: `android/app/build/outputs/apk/release/app-release.apk`

## הערות

- **Java 21 הוא LTS** (Long Term Support) - בטוח להתקין
- **לא צריך להסיר Java 17** - אפשר להחזיק כמה גרסאות
- **Gradle יבחר אוטומטית** את הגרסה הנכונה לפי `gradle.properties`
