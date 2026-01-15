# 🔄 בנייה מחדש ב-Xcode - עדכון גרסה וסימן מטבע

## ✅ מה כבר בוצע:
- ✅ הגרסה עודכנה ל-4.0.24 בכל הקבצים
- ✅ קוד סימן המטבע הדינמי נוסף
- ✅ Build הושלם - dist/ נוצר
- ✅ Capacitor sync הושלם - קבצים הועתקו ל-iOS

## 🔧 מה לעשות עכשיו ב-Xcode:

### שלב 1: נקה Build מלא
1. **Product → Clean Build Folder** (Shift+Cmd+K)
   - זה ימחק את כל הקבצים הישנים

### שלב 2: מחק DerivedData (אם צריך)
```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/App-*
```

### שלב 3: סגור ופתח מחדש את Xcode
1. סגור את Xcode לחלוטין
2. פתח מחדש:
   ```bash
   cd "/Users/itzhakbachar/Family Bank/kids-money-manager"
   npx cap open ios
   ```

### שלב 4: בנה מחדש
1. **Product → Clean Build Folder** (Shift+Cmd+K) - שוב
2. **Product → Build** (Cmd+B)
3. בדוק שאין שגיאות

### שלב 5: הרץ
1. בחר Simulator (iPhone 15 Pro, iPhone 16 Pro, וכו')
2. **Product → Run** (Cmd+R)

## 🔍 איך לבדוק שהכל עובד:

### בדיקת גרסה:
- פתח את האפליקציה
- חפש "גרסה 4.0.24" או "Version 4.0.24" במסך
- אם עדיין רואה 4.0.23, זה cache - נסה:
  1. מחק את האפליקציה מה-Simulator
  2. Product → Clean Build Folder
  3. בנה והרץ מחדש

### בדיקת סימן מטבע:
- שנה שפה (לחץ על כפתור השפה)
- בדוק שסימן המטבע משתנה:
  - עברית: ₪ (שקל)
  - אנגלית: $ (דולר)

## ⚠️ אם עדיין לא עובד:

### פתרון נוסף: מחק את האפליקציה מה-Simulator
1. ב-Simulator: לחץ לחיצה ארוכה על האפליקציה
2. לחץ על ה-X כדי למחוק
3. בנה והרץ מחדש

### פתרון נוסף: Reset Simulator
1. Device → Erase All Content and Settings...
2. בנה והרץ מחדש

---

**לאחר כל השלבים האלה, הגרסה צריכה להיות 4.0.24 וסימן המטבע צריך להשתנות לפי השפה.**
