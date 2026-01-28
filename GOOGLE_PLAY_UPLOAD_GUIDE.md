# מה להעלות ל-Google Play Console

## 📦 מה צריך להעלות?

ב-Google Play Console צריך להעלות **AAB (Android App Bundle)** - זה הפורמט המומלץ של Google.

### AAB vs APK:
- **AAB (Android App Bundle)** - מומלץ! Google ייצור APK אופטימלי לכל מכשיר
- **APK** - עובד, אבל AAB טוב יותר (קטן יותר, מותאם למכשיר)

---

## 🔨 איך ליצור AAB?

### אופציה 1: דרך Android Studio (מומלץ)

1. **פתח את הפרויקט ב-Android Studio:**
   ```bash
   # פתח את Android Studio
   # File → Open → בחר את התיקייה: android/
   ```

2. **בנה AAB:**
   - `Build` → `Generate Signed Bundle / APK`
   - בחר **"Android App Bundle"** (לא APK!)
   - בחר את ה-keystore שלך (`android/release.keystore`)
   - הזן את הסיסמה
   - בחר `prodRelease` variant (או `release`)
   - לחץ `Finish`
   - ה-AAB יישמר ב: `android/app/release/app-release.aab`

### אופציה 2: דרך שורת הפקודה

```bash
cd android
./gradlew bundleProdRelease

# ה-AAB יישמר ב:
# android/app/build/outputs/bundle/prodRelease/app-prod-release.aab
```

---

## 📋 שלבים להעלאה

### 1. יצירת Internal Testing Release

1. לך ל-Google Play Console
2. בחר את האפליקציה שלך
3. לך ל-`Testing` → `Internal testing`
4. לחץ `Create new release`

### 2. העלאת AAB

1. **בשדה "App bundles":**
   - גרור ושחרר את קובץ ה-AAB
   - או לחץ `Upload` ובחר את הקובץ
   - או לחץ `Add from library` אם כבר העלית בעבר

2. **המתן לעיבוד:**
   - Google יעבד את ה-AAB
   - זה יכול לקחת כמה דקות

### 3. Release name (שם השחרור)

**דוגמאות:**
```
Version 5.0.9
```
או:
```
5.0.9 - Initial Release
```

**הערות:**
- עד 50 תווים
- זה לא מוצג למשתמשים
- רק לזיהוי פנימי שלך

### 4. Release notes (הערות שחרור) - אופציונלי

אם זה השחרור הראשון, אפשר לכתוב:
```
Initial release of Family Bank app.
```

או:
```
First version of Family Bank - Money management for kids.
```

---

## ✅ רשימת בדיקה לפני העלאה

- [ ] AAB נבנה בהצלחה
- [ ] AAB חתום עם keystore
- [ ] בדקת את האפליקציה על מכשיר לפני העלאה
- [ ] גרסה נכונה ב-`build.gradle` (versionCode, versionName)
- [ ] Application ID נכון

---

## 🔍 איפה נמצא ה-AAB?

אחרי בנייה, ה-AAB יהיה ב:

**אם בנית דרך Android Studio:**
```
android/app/release/app-release.aab
```

**אם בנית דרך שורת פקודה:**
```
android/app/build/outputs/bundle/prodRelease/app-prod-release.aab
```

---

## ⚠️ חשוב!

1. **Keystore:**
   - צריך keystore חתום
   - שמור את ה-keystore במקום בטוח!
   - תצטרך אותו לכל עדכון עתידי

2. **גרסה:**
   - כל AAB חדש צריך `versionCode` גבוה יותר
   - `versionName` יכול להיות אותו דבר (אבל מומלץ לעדכן)

3. **בדיקה:**
   - בדוק את האפליקציה על מכשיר לפני העלאה
   - ודא שהכל עובד

---

## 🚀 אחרי העלאה

1. **Preview and confirm:**
   - בדוק את הפרטים
   - לחץ `Save` או `Start rollout`

2. **הוספת Testers:**
   - הוסף testers ל-Internal testing
   - הם יקבלו קישור להוריד את האפליקציה

3. **בדיקה:**
   - Testers יוכלו להוריד ולבדוק
   - אסף feedback

4. **Production:**
   - אחרי בדיקה מוצלחת, העלה ל-Production
   - אותו תהליך, אבל ל-Production release

---

## 💡 טיפים

1. **תמיד בנה AAB, לא APK** - זה הפורמט המומלץ
2. **בדוק לפני העלאה** - ודא שהאפליקציה עובדת
3. **שמור את ה-keystore** - תצטרך אותו לכל עדכון
4. **עדכן versionCode** - כל שחרור חדש צריך מספר גבוה יותר

---

**בהצלחה עם ההעלאה! 🚀**
