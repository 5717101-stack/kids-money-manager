# 📦 ניהול גרסאות - Single Source of Truth

## ✅ מה שונה?

עכשיו **כל מספרי הגרסה** נשלפים ממקום אחד בלבד: `package.json`

## 📍 המקור המרכזי

**`package.json`** - זה המקום היחיד שבו צריך לעדכן את הגרסה:
```json
{
  "version": "3.4.65"
}
```

## 🔄 איך זה עובד?

1. **`src/constants.js`** - קורא את הגרסה מ-`package.json`
2. **כל הקומפוננטים** - מייבאים את `APP_VERSION` מ-`constants.js`

## 📝 קבצים שמשתמשים בגרסה

### Frontend (React):
- ✅ `src/components/OTPVerification.jsx`
- ✅ `src/components/PhoneLogin.jsx`
- ✅ `src/components/WelcomeScreen.jsx`
- ✅ `src/components/ChildPasswordLogin.jsx`
- ✅ `src/components/Sidebar.jsx`

### Backend:
- ✅ `server/server.js` - כבר קורא מ-`package.json` (לא שונה)

### Mobile:
- ⚠️ `android/app/build.gradle` - צריך עדכון ידני (versionName)
- ⚠️ `ios/App/App.xcodeproj/project.pbxproj` - צריך עדכון ידני (MARKETING_VERSION)

## 🚀 איך לעדכן גרסה?

### שלב 1: עדכן את `package.json`
```bash
# ערוך את package.json
# שנה את "version": "3.4.65" לגרסה החדשה
```

### שלב 2: בנה מחדש
```bash
npm run build
npx cap sync
```

### שלב 3: עדכן Mobile (אופציונלי - רק אם צריך)
- **Android**: עדכן `android/app/build.gradle` → `versionName`
- **iOS**: עדכן `ios/App/App.xcodeproj/project.pbxproj` → `MARKETING_VERSION`

## 💡 יתרונות

✅ **מקור אחד** - עדכון במקום אחד מעדכן הכל  
✅ **פחות שגיאות** - אין סיכון לשכוח מקום  
✅ **אוטומטי** - ה-build קורא את הגרסה אוטומטית  
✅ **קל לתחזוקה** - לא צריך לחפש בכל הקבצים  

## ⚠️ הערות

- **Mobile apps** (Android/iOS) עדיין דורשים עדכון ידני ב-build files
- זה נורמלי כי הם לא חלק מה-JavaScript bundle
- אפשר ליצור סקריפט לעדכון אוטומטי בעתיד
