# השלבים הבאים - אפליקציית מובייל

## ✅ מה שכבר בוצע:

1. ✅ Capacitor הותקן
2. ✅ פלטפורמות iOS ו-Android נוספו
3. ✅ API URL עודכן ל-Railway
4. ✅ תיקיות ios/ ו-android/ נוצרו

## 🚀 השלבים הבאים:

### שלב 1: שמירת השינויים ב-GitHub

```bash
cd ~/Projects/kids-money-manager

# בדוק מה השתנה
git status

# הוסף את כל השינויים
git add .

# צור commit
git commit -m "הוספת תמיכה באפליקציית מובייל (iOS/Android)"

# דחוף ל-GitHub
git push origin main
```

### שלב 2: במשרד - משיכת השינויים

```bash
cd /path/to/project

# משוך את השינויים
git pull

# התקן dependencies (אם יש חדשים)
npm install
```

### שלב 3: פתיחת פרויקט ב-Xcode (iOS)

```bash
cd ~/Projects/kids-money-manager
export PATH="$HOME/.local/node22/bin:$PATH"  # אם צריך
npm run ios
```

או:
```bash
open ios/App/App.xcworkspace
```

### שלב 4: הגדרת Signing & Capabilities ב-Xcode

1. פתח את Xcode
2. בחר את הפרויקט (App) בתפריט השמאלי
3. בחר את ה-Target "App"
4. לחץ על **"Signing & Capabilities"**
5. סמן **"Automatically manage signing"**
6. בחר את **Team** שלך (Apple Developer Account)

### שלב 5: הרצה על Simulator

1. ב-Xcode, בחר **Simulator** (iPhone 14 Pro, וכו')
2. לחץ **▶️ Run** (Cmd+R)
3. האפליקציה תיפתח ב-Simulator

### שלב 6: בנייה ל-TestFlight (להפצה)

1. ב-Xcode: **Product** → **Archive**
2. המתן לסיום הבנייה
3. ב-Organizer, לחץ **"Distribute App"**
4. בחר **"App Store Connect"**
5. העלה ל-TestFlight

## 📱 לפתח Android:

```bash
cd ~/Projects/kids-money-manager
export PATH="$HOME/.local/node22/bin:$PATH"  # אם צריך
npm run android
```

או פתח את Android Studio:
```bash
open -a "Android Studio" android/
```

## 🔄 עדכונים עתידיים:

לאחר כל שינוי בקוד:

```bash
# 1. בנה את האפליקציה
npm run build

# 2. סנכרן עם Capacitor
export PATH="$HOME/.local/node22/bin:$PATH"
npx cap sync

# 3. עדכן ב-Xcode/Android Studio
```

## ⚠️ הערות חשובות:

- **Node.js 22 נדרש** - השתמש ב: `export PATH="$HOME/.local/node22/bin:$PATH"`
- **API URL** כבר מוגדר ל-Railway
- **App ID**: `com.bachar.kidsmoneymanager`
- **תיקיות ios/ ו-android/** לא נשמרות ב-Git (מוגנות ב-.gitignore)

## 📚 מדריכים נוספים:

- `MOBILE_APP_GUIDE.md` - מדריך מפורט
- `MOBILE_SETUP_STEPS.md` - שלבי התקנה מהירים

## 🆘 פתרון בעיות:

### "Node.js 22 required"
```bash
export PATH="$HOME/.local/node22/bin:$PATH"
```

### "Could not find web assets"
```bash
npm run build
npx cap sync
```

### "No signing certificate"
- היכנס ל-[Apple Developer](https://developer.apple.com)
- צור Certificate חדש
