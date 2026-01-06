# איפה למצוא את הגדרת Job ב-Railway

## מיקום ההגדרה

### אפשרות 1: Settings → Service Configuration
1. היכנס ל-Railway Dashboard
2. בחר את הפרויקט שלך
3. בחר את השירות `kids-money-manager-server`
4. לחץ על **Settings** (בתפריט השמאלי)
5. תחת **Service Configuration** או **General**, חפש:
   - **Service Type**
   - **Deployment Type**
   - **Run Type**

### אפשרות 2: Deployments → Settings
1. היכנס ל-Railway Dashboard
2. בחר את הפרויקט שלך
3. בחר את השירות `kids-money-manager-server`
4. לחץ על **Deployments**
5. לחץ על ה-Deployment האחרון
6. לחץ על **Settings** או **Configure**
7. חפש **Service Type** או **Run Type**

### אפשרות 3: Service Settings → Advanced
1. היכנס ל-Railway Dashboard
2. בחר את הפרויקט שלך
3. בחר את השירות `kids-money-manager-server`
4. לחץ על **Settings**
5. גלול למטה ל-**Advanced** או **Service Configuration**
6. חפש **Service Type** או **Run Type**

### אפשרות 4: אם לא מוצאים
אם לא מוצאים את ההגדרה, זה יכול להיות:
1. **השירות כבר מוגדר כ-Web Service** (ברירת המחדל)
2. **ההגדרה נמצאת במקום אחר** - נסה לחפש ב-Settings → Health Check
3. **צריך ליצור שירות חדש** - אולי השירות הנוכחי מוגדר כ-Job ולא ניתן לשנות

## איך לדעת אם זה Job או Web Service?

### סימנים שזה Job:
- הקונטיינר נעצר אחרי זמן קצר (30-300 שניות)
- אין health check calls בלוגים
- Railway לא בודק health check

### סימנים שזה Web Service:
- הקונטיינר נשאר בחיים
- יש health check calls בלוגים
- Railway בודק health check כל כמה שניות

## פתרון חלופי: יצירת שירות חדש

אם לא מוצאים את ההגדרה או לא ניתן לשנות אותה:

1. **צור שירות חדש:**
   - ב-Railway Dashboard, לחץ על **New Service**
   - בחר **GitHub Repo** או **Deploy from GitHub**
   - בחר את ה-repository שלך
   - ודא שהשירות מוגדר כ-Web Service (לא Job)

2. **הגדר את השירות:**
   - Root Directory: `server`
   - Start Command: `node server.js`
   - Health Check Path: `/health`
   - Health Check Timeout: 300 שניות
   - Health Check Interval: 5 שניות

3. **הסר את השירות הישן:**
   - לאחר שהשירות החדש עובד, הסר את השירות הישן

## אם עדיין לא עובד

אם עדיין לא עובד אחרי כל זה, הבעיה יכולה להיות:
1. **Health Check לא עובד** - בדוק את הלוגים
2. **השירות לא מאזין ל-PORT הנכון** - בדוק שהשרת מאזין ל-`process.env.PORT`
3. **בעיה ב-Railway עצמו** - פנה לתמיכה של Railway

## צילום מסך

אם אתה יכול, שלח צילום מסך של:
- Settings → Service Configuration
- Settings → Health Check
- Deployments → האחרון

זה יעזור לזהות את הבעיה.

