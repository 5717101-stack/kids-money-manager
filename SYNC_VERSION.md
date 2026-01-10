# 🔄 סנכרון גרסה - מדריך מלא

## 📍 מקור הגרסה

הגרסה נשלפת **אוטומטית** מ-`package.json` דרך `src/constants.js`:

```javascript
// src/constants.js
import packageJson from '../package.json';
export const APP_VERSION = packageJson.version;
```

## ✅ בדיקת סנכרון מלא

### 1. בדוק את package.json
```bash
cat package.json | grep '"version"'
```
**צריך להיות:** `"version": "3.7.7"`

### 2. בדוק את dist (לאחר build)
```bash
npm run build
grep -o "ov=\"[^\"]*\"" dist/assets/*.js
```
**צריך להיות:** `ov="3.7.7"`

### 3. העתק ל-iOS
```bash
rm -rf ios/App/App/public/assets ios/App/App/public/index.html
cp -r dist/assets ios/App/App/public/
cp dist/index.html ios/App/App/public/
```

### 4. בדוק את iOS
```bash
grep -o "ov=\"[^\"]*\"" ios/App/App/public/assets/*.js
```
**צריך להיות:** `ov="3.7.7"`

### 5. בדוק את Android
```bash
grep "versionName" android/app/build.gradle
```
**צריך להיות:** `versionName "3.7.7"`

### 6. בדוק את iOS Xcode
```bash
grep "MARKETING_VERSION" ios/App/App.xcodeproj/project.pbxproj
```
**צריך להיות:** `MARKETING_VERSION = 3.7.7;`

## 🚨 אם הגרסה עדיין לא נכונה

### שלב 1: Clean Build מלא
```bash
# סגור את Xcode
# מחק את האפליקציה מהמכשיר/סימולטור

# ניקוי קבצים
cd ios/App
rm -rf DerivedData build
rm -rf ~/Library/Developer/Xcode/DerivedData/*
```

### שלב 2: Build מחדש
```bash
cd /Users/itzhakbachar/Projects/kids-money-manager
npm run build
rm -rf ios/App/App/public/assets ios/App/App/public/index.html
cp -r dist/assets ios/App/App/public/
cp dist/index.html ios/App/App/public/
```

### שלב 3: Clean Build ב-Xcode
1. פתח את Xcode
2. **Product → Clean Build Folder** (Shift+Cmd+K)
3. **Product → Build** (Cmd+B)
4. **Product → Run** (Cmd+R)

### שלב 4: אם עדיין לא עובד
1. מחק את האפליקציה מהמכשיר לחלוטין
2. כבה את המכשיר והדלק אותו מחדש
3. התקן את האפליקציה מחדש

## 📝 רשימת בדיקה

- [ ] `package.json` → `"version": "3.7.7"`
- [ ] `dist/assets/*.js` → `ov="3.7.7"`
- [ ] `ios/App/App/public/assets/*.js` → `ov="3.7.7"`
- [ ] `android/app/build.gradle` → `versionName "3.7.7"`
- [ ] `ios/App/App.xcodeproj/project.pbxproj` → `MARKETING_VERSION = 3.7.7;`
- [ ] Clean Build ב-Xcode
- [ ] מחק את האפליקציה מהמכשיר
- [ ] התקן מחדש

## 💡 טיפים

1. **תמיד** הרץ `npm run build` לפני העתקה ל-iOS
2. **תמיד** מחק את הקבצים הישנים לפני העתקה
3. **תמיד** Clean Build ב-Xcode אחרי עדכון קבצים
4. **תמיד** מחק את האפליקציה מהמכשיר אחרי עדכון גרסה
