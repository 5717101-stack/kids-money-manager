# 🚀 בניית APK - גרסה 4.0.26

## ⚡ דרך מהירה: Android Studio

Java לא מותקן במחשב, אז צריך לבנות דרך Android Studio:

### שלבים:

1. **פתח את הפרויקט:**
   ```bash
   cd "/Users/itzhakbachar/Family Bank/kids-money-manager"
   npx cap open android
   ```

2. **בחר Build Variant:**
   - **View → Tool Windows → Build Variants**
   - בחר **"prodRelease"** (לא debug!)

3. **בנה APK:**
   - **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - המתן לסיום הבנייה (יכול לקחת כמה דקות)

4. **מצא את ה-APK:**
   - לחץ על **"locate"** בהודעה שנפתחת
   - או: `android/app/build/outputs/apk/prod/release/app-prod-release.apk`

5. **העתק לשולחן העבודה:**
   ```bash
   VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
   mkdir -p ~/Desktop/apk
   cp android/app/build/outputs/apk/prod/release/app-prod-release.apk ~/Desktop/apk/Family-Bank-${VERSION}.apk
   ```

## ✅ מה כבר מוכן:

- ✅ Build הושלם - הקוד ב-`dist/`
- ✅ Capacitor sync הושלם - Android מעודכן
- ✅ Signing configuration מוכן - `android/key.properties`
- ✅ `build.gradle` מוגדר לחתימה
- ✅ תיקייה נוצרה: `~/Desktop/apk`

## 📱 אחרי הבנייה

ה-APK יהיה ב: `~/Desktop/apk/Family-Bank-4.0.26.apk`

## ⚠️ חשוב:

- **בחר "prodRelease"** - לא debug!
- APK חתום = מתקין נכון
- APK לא חתום = "package invalid"

---

**עכשיו פתח Android Studio ובנה את ה-APK!**
