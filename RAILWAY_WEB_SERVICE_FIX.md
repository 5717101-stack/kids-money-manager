# תיקון: הגדרת השירות כ-Web Service ב-Railway

## הבעיה
השרת רץ 95 שניות לפני שהוא מקבל SIGTERM. זה אומר ש-Railway לא מזהה את השירות כ-Web Service.

## הפתרון
צריך לוודא שהשירות מוגדר כ-Web Service ולא כ-Job.

## שלבים

1. **היכנס ל-Railway Dashboard**
   - לך לפרויקט שלך
   - בחר את השירות `kids-money-manager-server`

2. **Settings → Service Type**
   - לחץ על Settings
   - מצא את "Service Type" או "Service Configuration"
   - ודא שהשירות מוגדר כ-Web Service (לא Job)
   - אם זה Job, שנה ל-Web Service

3. **Settings → Health Check**
   - ודא ש-Health Check Path הוא: `/health`
   - ודא ש-Health Check Timeout הוא: 300 שניות (או יותר)
   - ודא ש-Health Check Interval הוא: 5 שניות

4. **Redeploy**
   - לחץ על "Redeploy" או המתן ל-auto deploy
   - השרת אמור להישאר בחיים

## למה זה חשוב?
- Job = Railway מצפה שהתהליך יסתיים אחרי ביצוע המשימה
- Web Service = Railway מצפה שהתהליך ימשיך לרוץ
- אם השירות מוגדר כ-Job, Railway יעצור אותו אחרי זמן קצר

## אם עדיין לא עובד
אם השירות כבר מוגדר כ-Web Service ועדיין לא עובד:
1. בדוק את הלוגים - האם health check נקרא?
2. בדוק את ה-Settings - האם health check path נכון?
3. נסה Manual Redeploy

