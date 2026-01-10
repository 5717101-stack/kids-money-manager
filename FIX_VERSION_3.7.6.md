# תיקון גרסה 3.7.6 ב-iOS

## ✅ מה כבר מעודכן
- ✅ `package.json`: 3.7.6
- ✅ `dist/assets`: 3.7.6
- ✅ `ios/App/App/public/assets`: 3.7.6 (עודכן עכשיו)
- ✅ `ios/App/App.xcodeproj/project.pbxproj`: MARKETING_VERSION = 3.7.6
- ✅ `android/app/build.gradle`: versionName "3.7.6"

## 🔧 מה לעשות עכשיו (ניקוי מלא)

### שלב 1: סגור את Xcode לחלוטין
1. סגור את כל חלונות Xcode
2. ודא שאין תהליכי Xcode שרצים

### שלב 2: ניקוי קבצים ב-Terminal
פתח Terminal והרץ:
```bash
cd /Users/itzhakbachar/Projects/kids-money-manager/ios/App
rm -rf DerivedData
rm -rf build
rm -rf ~/Library/Developer/Xcode/DerivedData/*
```

### שלב 3: מחק את האפליקציה מהמכשיר/סימולטור
1. אם האפליקציה מותקנת על המכשיר/סימולטור, מחק אותה לחלוטין
2. זה יבטיח שהאפליקציה לא תטען cache ישן

### שלב 4: פתח את Xcode מחדש
```bash
cd /Users/itzhakbachar/Projects/kids-money-manager
open ios/App/App.xcworkspace
```

### שלב 5: Clean Build ב-Xcode
1. ב-Xcode: **Product → Clean Build Folder** (Shift+Cmd+K)
2. חכה שהניקוי יסתיים (יכול לקחת כמה שניות)

### שלב 6: Build & Run
1. ב-Xcode: **Product → Build** (Cmd+B)
2. אחרי שהבנייה מסתיימת: **Product → Run** (Cmd+R)

### שלב 7: אם עדיין לא עובד
אם עדיין מופיעה גרסה 3.7.5, נסה:

1. סגור את Xcode
2. הרץ ב-Terminal:
   ```bash
   cd /Users/itzhakbachar/Projects/kids-money-manager
   rm -rf ios/App/DerivedData
   rm -rf ios/App/build
   rm -rf ios/App/App/public/assets
   npm run build
   cp -r dist/assets ios/App/App/public/
   cp dist/index.html ios/App/App/public/
   ```
3. פתח את Xcode מחדש
4. Clean Build Folder
5. Build & Run

### שלב 8: אם עדיין לא עובד (ניקוי מלא)
אם עדיין מופיעה 3.7.5, זה cache של WebView:

1. מחק את האפליקציה מהמכשיר
2. כבה את המכשיר והדלק אותו מחדש
3. התקן את האפליקציה מחדש

## ✅ וידוא שהגרסה נכונה
לאחר Build & Run, בדוק:
- בתפריט הצד: "גרסה 3.7.6"
- במסך הלוגין: "גרסה 3.7.6"
- במסך OTP: "גרסה 3.7.6"

אם עדיין מופיעה 3.7.5, זה cache של WebView - צריך למחוק את האפליקציה ולהתקין מחדש.
