# הוראות להחלפת סמל האפליקציה

## אופציה 1: שימוש בסקריפט (אוטומטי)

1. שמור את תמונת קופת החיסכון הסגולה כקובץ PNG (רצוי 1024x1024 פיקסלים)
2. הרץ את הסקריפט:
   ```bash
   ./replace_app_icon.sh path/to/your/icon.png
   ```

## אופציה 2: החלפה ידנית

### iOS:
1. פתח את Xcode: `npx cap open ios`
2. בחר את `AppIcon` ב-Assets.xcassets
3. גרור את התמונה החדשה (1024x1024) לתוך ה-AppIcon

### Android:
1. החלף את הקבצים ב-`android/app/src/main/res/mipmap-*/`:
   - `ic_launcher.png` - 48x48 (mdpi), 72x72 (hdpi), 96x96 (xhdpi), 144x144 (xxhdpi), 192x192 (xxxhdpi)
   - `ic_launcher_round.png` - אותם גדלים
   - `ic_launcher_foreground.png` - 108x108 (mdpi), 162x162 (hdpi), 216x216 (xhdpi), 432x432 (xxhdpi/xxxhdpi)

## הערות:
- התמונה צריכה להיות בפורמט PNG
- מומלץ שהתמונה תהיה 1024x1024 פיקסלים לפחות
- התמונה תהיה מעוגלת אוטומטית ב-Android (אם מוגדר כך)
