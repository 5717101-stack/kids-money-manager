# מדריך מפורט להעלאה ל-Google Play Store

## 📋 דרישות מוקדמות

### 1. חשבון Google Play Console
- צריך חשבון מפתח ב-Google Play Console
- עלות: $25 חד פעמי (תשלום חד פעמי לכל החיים)
- כתובת: https://play.google.com/console

### 2. APK חתום (Signed APK)
- צריך APK חתום עם keystore
- לא ניתן להעלות APK לא חתום

---

## 🔨 שלב 1: בניית APK חתום

### אופציה A: בנייה דרך Android Studio (מומלץ)

1. **פתח את הפרויקט ב-Android Studio:**
   ```bash
   # פתח את Android Studio
   # File → Open → בחר את התיקייה: android/
   ```

2. **בנה APK חתום:**
   - `Build` → `Generate Signed Bundle / APK`
   - בחר `APK`
   - בחר את ה-keystore שלך (`android/release.keystore`)
   - הזן את הסיסמה
   - בחר `release` variant
   - לחץ `Finish`
   - ה-APK יישמר ב: `android/app/release/app-release.apk`

### אופציה B: בנייה דרך שורת הפקודה

```bash
cd android
./gradlew assembleRelease

# ה-APK יישמר ב:
# android/app/build/outputs/apk/release/app-release.apk
```

---

## 📱 שלב 2: הכנת צילומי מסך

### גדלים נדרשים:

**Phone (טלפון):**
- לפחות 2 צילומי מסך
- גודל: 320dp - 3840dp (רוחב)
- יחס גובה-רוחב: 16:9 או 9:16

**Tablet (טאבלט):**
- לפחות 2 צילומי מסך
- גודל: 600dp - 2560dp (רוחב)

**Feature Graphic (תמונה ראשית):**
- גודל: 1024 x 500 פיקסלים
- פורמט: PNG או JPG
- ללא טקסט (רק תמונה)

**Icon (אייקון):**
- גודל: 512 x 512 פיקסלים
- פורמט: PNG (ללא שקיפות)

### יצירת צילומי מסך:

אם יש לך צילומי מסך לאייפון, אפשר להשתמש בהם:
- iPhone screenshots יכולים לעבוד גם לאנדרואיד
- Google Play יאפשר לך להעלות אותם

---

## 🚀 שלב 3: העלאה ל-Google Play Console

### 1. התחברות ל-Google Play Console
- לך ל: https://play.google.com/console
- התחבר עם חשבון Google שלך
- אם אין לך חשבון מפתח, תתבקש לשלם $25

### 2. יצירת אפליקציה חדשה
- לחץ על `Create app`
- מלא את הפרטים:
  - **App name:** Family Bank (או השם שברצונך)
  - **Default language:** Hebrew (עברית)
  - **App or game:** App
  - **Free or paid:** Free (או Paid)
  - לחץ `Create app`

### 3. מילוי פרטי האפליקציה

#### Store listing (מידע בחנות):
- **App name:** Family Bank
- **Short description:** תיאור קצר (80 תווים מקסימום)
- **Full description:** תיאור מלא (4000 תווים מקסימום)
- **App icon:** העלה אייקון 512x512
- **Feature graphic:** העלה תמונה 1024x500
- **Screenshots:** העלה צילומי מסך (לפחות 2)
- **Category:** Finance (פיננסים)
- **Contact details:** אימייל לתמיכה

#### Content rating (דירוג תוכן):
- מלא שאלון על תוכן האפליקציה
- Google יקבע את הדירוג (למשל: Everyone)

#### Privacy policy (מדיניות פרטיות):
- **חובה!** צריך קישור למדיניות פרטיות
- הקישור שלך: https://5717101-stack.github.io/family-bank-support-/privacy.html

### 4. העלאת APK

#### Production (ייצור):
1. לך ל-`Production` → `Create new release`
2. העלה את ה-APK החתום
3. מלא `Release notes` (הערות שחרור)
4. לחץ `Save`

#### Testing (בדיקה - אופציונלי):
- אפשר להעלות ל-`Internal testing` או `Closed testing` קודם
- זה מאפשר לבדוק את האפליקציה לפני שחרור

### 5. בדיקות נדרשות

#### App content (תוכן האפליקציה):
- **Target audience:** בחר את קהל היעד (ילדים, משפחות)
- **Content rating:** מלא שאלון
- **Data safety:** מלא פרטים על איסוף נתונים

#### Store settings (הגדרות חנות):
- **Pricing:** Free (או בחר מחיר)
- **Countries:** בחר מדינות (מומלץ: All countries)

---

## ✅ שלב 4: הגשת האפליקציה לבדיקה

1. **בדוק שכל הסעיפים מולאו:**
   - ✅ Store listing
   - ✅ Content rating
   - ✅ Privacy policy
   - ✅ APK uploaded
   - ✅ App icon
   - ✅ Screenshots

2. **לחץ על `Submit for review`**

3. **המתן לאישור:**
   - Google יבדוק את האפליקציה
   - זה יכול לקחת כמה שעות עד כמה ימים
   - תקבל אימייל כשהאפליקציה תאושר

---

## 📋 רשימת בדיקה לפני הגשה

- [ ] APK חתום נבנה בהצלחה
- [ ] אייקון 512x512 מוכן
- [ ] Feature graphic 1024x500 מוכן
- [ ] לפחות 2 צילומי מסך מוכנים
- [ ] תיאור קצר נכתב (80 תווים)
- [ ] תיאור מלא נכתב (4000 תווים)
- [ ] Privacy policy URL מוכן
- [ ] Content rating מולא
- [ ] Data safety מולא
- [ ] APK הועלה ל-Production

---

## 🔗 קישורים שימושיים

- **Google Play Console:** https://play.google.com/console
- **Privacy Policy:** https://5717101-stack.github.io/family-bank-support-/privacy.html
- **Support Page:** https://5717101-stack.github.io/family-bank-support-/

---

## 💡 טיפים

1. **בדיקה לפני שחרור:**
   - העלה ל-Internal testing קודם
   - בדוק את האפליקציה על מכשיר אמיתי
   - ודא שהכל עובד

2. **תמונות:**
   - השתמש בצילומי מסך איכותיים
   - Feature graphic צריך להיות מושך עין
   - אייקון צריך להיות ברור גם בגודל קטן

3. **תיאורים:**
   - כתוב תיאור מפורט ומעניין
   - השתמש במילות מפתח רלוונטיות
   - הוסף screenshots שמראים את התכונות העיקריות

4. **עדכונים:**
   - אחרי השחרור, כל עדכון צריך APK חדש
   - עדכן את `versionCode` ו-`versionName` ב-`build.gradle`
   - העלה APK חדש ל-Production

---

## 🆘 בעיות נפוצות

### APK לא חתום:
- צריך לבנות APK עם keystore
- לא ניתן להעלות APK לא חתום

### Privacy policy חסר:
- חובה להעלות קישור למדיניות פרטיות
- הקישור שלך: https://5717101-stack.github.io/family-bank-support-/privacy.html

### Content rating לא מולא:
- צריך למלא שאלון על תוכן האפליקציה
- Google יקבע את הדירוג

### Screenshots חסרים:
- צריך לפחות 2 צילומי מסך
- אפשר להשתמש בצילומי מסך מאייפון

---

## 📞 תמיכה

אם נתקלת בבעיות:
1. בדוק את ה-logs ב-Google Play Console
2. קרא את ההודעות שגיאה
3. ודא שכל הסעיפים מולאו

---

**בהצלחה עם ההעלאה ל-Google Play! 🚀**
