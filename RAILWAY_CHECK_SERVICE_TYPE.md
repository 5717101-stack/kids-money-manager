# איך לבדוק את סוג השירות ב-Railway

## איפה לבדוק

### אפשרות 1: Settings → General
1. היכנס ל-Railway Dashboard
2. בחר את השירות `kids-money-manager-server`
3. לחץ על **Settings** (בתפריט השמאלי)
4. תחת **General** או **Service Configuration**, חפש:
   - **Service Type**
   - **Service Configuration**
   - **Deployment Type**

### אפשרות 2: Deployments
1. היכנס ל-Railway Dashboard
2. בחר את השירות `kids-money-manager-server`
3. לחץ על **Deployments**
4. בדוק את ה-Deployment האחרון - האם יש שם משהו על "Job" או "Web Service"?

### אפשרות 3: Variables
1. היכנס ל-Railway Dashboard
2. בחר את השירות `kids-money-manager-server`
3. לחץ על **Variables**
4. בדוק אם יש משתנה סביבה שקשור ל-Service Type

### אפשרות 4: Health Check Settings
1. היכנס ל-Railway Dashboard
2. בחר את השירות `kids-money-manager-server`
3. לחץ על **Settings**
4. תחת **Health Check** או **Deploy**, בדוק:
   - **Health Check Path**: צריך להיות `/health`
   - **Health Check Timeout**: צריך להיות 300 שניות
   - **Health Check Interval**: צריך להיות 5 שניות

## איך לדעת אם זה Job או Web Service?

### Job (לא נכון)
- Railway מצפה שהתהליך יסתיים אחרי ביצוע המשימה
- Railway יעצור את הקונטיינר אחרי זמן קצר (30-90 שניות)
- אין health check או health check לא עובד

### Web Service (נכון)
- Railway מצפה שהתהליך ימשיך לרוץ
- Railway בודק health check כל כמה שניות
- הקונטיינר נשאר בחיים כל עוד health check עונה

## אם לא מוצאים Service Type

אם לא מוצאים את Service Type, זה כנראה אומר שהשירות כבר מוגדר כ-Web Service (זה ברירת המחדל). הבעיה היא כנראה משהו אחר:

1. **Health Check לא עובד** - בדוק את ה-Settings → Health Check
2. **Health Check Path שגוי** - צריך להיות `/health`
3. **Health Check Timeout קצר מדי** - צריך להיות 300 שניות
4. **השירות לא מאזין ל-PORT הנכון** - בדוק שהשרת מאזין ל-`process.env.PORT`

## מה לעשות עכשיו

1. בדוק את ה-Settings → Health Check
2. ודא ש-Health Check Path הוא `/health`
3. ודא ש-Health Check Timeout הוא 300 שניות
4. ודא ש-Health Check Interval הוא 5 שניות
5. נסה Manual Redeploy

אם עדיין לא עובד, שלח צילום מסך של ה-Settings או תאר מה אתה רואה.

