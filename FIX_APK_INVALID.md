# 🔧 תיקון "Package Invalid" ב-Android

## הבעיה
APK לא מתקין ואומר "package invalid" - זה קורה כי ה-APK לא חתום (unsigned).

## ✅ מה כבר בוצע:
- ✅ Keystore נוצר: `android/app/release.keystore`
- ✅ key.properties נוצר: `android/key.properties`

## 📱 עכשיו צריך לבנות APK חתום:

### דרך 1: Android Studio (מומלץ)

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
   - המתן לסיום הבנייה

4. **מצא את ה-APK:**
   - לחץ על **"locate"** בהודעה
   - או: `android/app/build/outputs/apk/prod/release/app-prod-release.apk`

5. **העתק לשולחן העבודה:**
   ```bash
   VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
   mkdir -p ~/Desktop/apk
   cp android/app/build/outputs/apk/prod/release/app-prod-release.apk ~/Desktop/apk/Family-Bank-${VERSION}.apk
   ```

### דרך 2: Terminal (אם יש Java)

```bash
cd android
./gradlew assembleProdRelease
```

## ⚠️ חשוב:
- **בחר "prodRelease"** - לא debug!
- APK חתום = מתקין נכון
- APK לא חתום = "package invalid"

## 🔍 איך לבדוק:
אחרי הבנייה, ה-APK צריך להיות חתום. אם עדיין לא עובד:
1. ודא שבחרת **prodRelease** variant
2. ודא ש-`android/key.properties` קיים
3. ודא ש-`android/app/release.keystore` קיים

---

**עכשיו בנה APK דרך Android Studio עם prodRelease variant!**
