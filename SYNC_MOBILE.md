# הוראות סנכרון לאפליקציה ניידת

## הבעיה שנמצאה:
נמצא קובץ ישן ב-`ios/App/App/public/assets/` עם גרסה 4.0.28 שלא התעדכן.

## מה בוצע:
1. ✅ נמחקו קבצים ישנים מ-`ios/App/App/public/`
2. ✅ נמחקו קבצים ישנים מ-`android/app/src/main/assets/`
3. ✅ נמחק Xcode DerivedData
4. ✅ נבנה מחדש הקוד עם גרסה 4.0.29
5. ✅ הועתקו קבצים חדשים ל-iOS ו-Android

## מה לעשות עכשיו:

### ב-Xcode:
1. פתח את הפרויקט: `ios/App/App.xcodeproj`
2. נקה את ה-build folder:
   - Product > Clean Build Folder (Shift+Cmd+K)
3. סגור את Xcode
4. פתח מחדש את Xcode
5. בנה מחדש:
   - Product > Build (Cmd+B)
6. התקן מחדש על המכשיר:
   - Product > Run (Cmd+R)

### אם עדיין לא עובד:
1. מחק את האפליקציה מהמכשיר
2. סגור את Xcode לחלוטין
3. פתח מחדש את Xcode
4. נקה build folder שוב
5. בנה והתקן מחדש

### לסנכרון אוטומטי (אם יש Node >= 22):
```bash
npx cap sync
```

### לסנכרון ידני (אם אין Node >= 22):
```bash
# העתק קבצים ל-iOS
cp -r dist/* ios/App/App/public/

# העתק קבצים ל-Android
mkdir -p android/app/src/main/assets
cp -r dist/* android/app/src/main/assets/
```
