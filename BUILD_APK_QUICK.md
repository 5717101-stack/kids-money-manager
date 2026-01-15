# 🚀 בניית APK - דרך מהירה

## ⚡ דרך מהירה: Android Studio

Java לא מותקן במחשב, אז צריך לבנות דרך Android Studio:

### שלבים:

1. **פתח את הפרויקט:**
   ```bash
   cd "/Users/itzhakbachar/Family Bank/kids-money-manager"
   npx cap open android
   ```

2. **בנה APK:**
   - **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - המתן לסיום הבנייה

3. **מצא את ה-APK:**
   - לחץ על **"locate"** בהודעה שנפתחת
   - או: `android/app/build/outputs/apk/release/app-release.apk`

4. **העתק לשולחן העבודה:**
   ```bash
   VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
   mkdir -p ~/Desktop/apk
   cp android/app/build/outputs/apk/release/app-release.apk ~/Desktop/apk/Family-Bank-${VERSION}.apk
   ```

## ✅ אחרי הבנייה

ה-APK יהיה ב: `~/Desktop/apk/Family-Bank-4.0.25.apk`
