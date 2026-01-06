# שלבי התקנה מהירים - אפליקציית מובייל

## שלב 1: התקנת Capacitor (5 דקות)

```bash
cd "/Users/itzikbachar/Test Cursor"

# התקן Capacitor
npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android

# התקן פלאגינים נחוצים
npm install @capacitor/app @capacitor/keyboard @capacitor/status-bar
```

## שלב 2: אתחול Capacitor (2 דקות)

```bash
npx cap init
```

**תשובות:**
- App name: `Kids Money Manager`
- App ID: `com.yourname.kidsmoneymanager` (החלף yourname בשם שלך)
- Web dir: `dist`

## שלב 3: בנייה וסינכרון (1 דקה)

```bash
npm run build
npx cap sync
```

## שלב 4: עדכון API URL

**חשוב!** פתח `src/utils/api.js` ומצא את השורה:
```javascript
const PRODUCTION_API = 'https://your-railway-app.up.railway.app/api';
```

**החלף** `your-railway-app` בכתובת האמיתית של Railway שלך.

## שלב 5: פתיחת פרויקטים

### iOS (דורש Mac + Xcode):
```bash
npm run ios
```

### Android:
```bash
npm run android
```

---

## הפצה למשתמשים

### iOS - TestFlight:
1. Xcode → Product → Archive
2. Distribute App → App Store Connect
3. App Store Connect → TestFlight → הוסף משתמשים

### Android - Internal Testing:
1. Android Studio → Build → Generate Signed Bundle
2. Google Play Console → Internal Testing → העלה AAB

---

**למדריך מפורט, ראה `MOBILE_APP_GUIDE.md`**

