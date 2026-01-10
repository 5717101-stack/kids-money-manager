# תיקון בעיית תצוגת הגרסה

## הבעיה
הגרסה המוצגת באפליקציה היא 3.7.3 למרות שהגרסה בקוד היא 3.7.5.

## מה תוקן
1. ✅ `package.json` - עודכן ל-3.7.5
2. ✅ `dist/assets` - נבנה מחדש עם 3.7.5
3. ✅ `ios/App/public/assets` - עודכן עם הקבצים החדשים (מחקתי קובץ ישן)
4. ✅ `android/app/build.gradle` - עודכן ל-3.7.5
5. ✅ `ios/App/App.xcodeproj/project.pbxproj` - עודכן ל-3.7.5

## מה לעשות עכשיו

### שלב 1: ניקוי מלא ב-Xcode
1. סגור את Xcode לחלוטין
2. פתח Terminal והרץ:
   ```bash
   cd /Users/itzhakbachar/Projects/kids-money-manager/ios/App
   rm -rf DerivedData
   rm -rf build
   ```
3. פתח את Xcode מחדש

### שלב 2: Clean Build ב-Xcode
1. ב-Xcode: **Product → Clean Build Folder** (Shift+Cmd+K)
2. חכה שהניקוי יסתיים

### שלב 3: מחק את האפליקציה מהמכשיר/סימולטור
1. אם האפליקציה מותקנת על המכשיר/סימולטור, מחק אותה לחלוטין
2. זה יבטיח שהאפליקציה לא תטען cache ישן

### שלב 4: Build & Run
1. ב-Xcode: **Product → Build** (Cmd+B)
2. אחרי שהבנייה מסתיימת: **Product → Run** (Cmd+R)

### שלב 5: אם עדיין לא עובד
אם עדיין מופיעה גרסה 3.7.3, נסה:

1. סגור את Xcode
2. הרץ Terminal:
   ```bash
   cd /Users/itzhakbachar/Projects/kids-money-manager
   rm -rf ios/App/DerivedData
   rm -rf ios/App/build
   rm -rf ios/App/public/assets
   npm run build
   cp -r dist/assets ios/App/public/
   ```
3. פתח את Xcode מחדש
4. Clean Build Folder
5. Build & Run

## וידוא שהגרסה נכונה
לאחר Build & Run, בדוק:
- בתפריט הצד: "גרסה 3.7.5"
- במסך הלוגין: "גרסה 3.7.5"
- במסך OTP: "גרסה 3.7.5"

אם עדיין מופיעה 3.7.3, זה cache של WebView. נסה:
1. מחק את האפליקציה מהמכשיר
2. כבה את המכשיר והדלק אותו מחדש
3. התקן את האפליקציה מחדש
