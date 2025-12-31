# יצירת Personal Access Token ל-GitHub

## למה צריך Token?
GitHub כבר לא מאפשר שימוש בסיסמה ל-Git operations. צריך Personal Access Token.

## שלב אחר שלב:

### שלב 1: היכנס ל-GitHub
1. פתח [GitHub.com](https://github.com)
2. התחבר לחשבון שלך

### שלב 2: פתח את Settings
1. לחץ על התמונה שלך בפינה הימנית העליונה
2. לחץ **"Settings"**

### שלב 3: פתח Developer settings
1. בתפריט השמאלי, גלול למטה
2. לחץ **"Developer settings"** (בתחתית)

### שלב 4: פתח Personal access tokens
1. בתפריט השמאלי, לחץ **"Personal access tokens"**
2. לחץ **"Tokens (classic)"**

### שלב 5: צור Token חדש
1. לחץ **"Generate new token"**
2. לחץ **"Generate new token (classic)"**

### שלב 6: הגדר את ה-Token
1. **Note:** הזן שם (למשל: "Kids Money Manager")
2. **Expiration:** בחר כמה זמן (למשל: 90 days או No expiration)
3. **Select scopes:** סמן את ה-checkbox:
   - ✅ **`repo`** (כל ה-repositories)
     - זה כולל: repo:status, repo_deployment, public_repo, repo:invite, security_events
4. גלול למטה ולחץ **"Generate token"**

### שלב 7: העתק את ה-Token
⚠️ **חשוב:** תראה את ה-Token רק פעם אחת!
1. העתק את ה-Token מיד (נראה כמו: `ghp_xxxxxxxxxxxxxxxxxxxx`)
2. שמור אותו במקום בטוח

### שלב 8: השתמש ב-Token
כשאתה מריץ:
```bash
git push --set-upstream origin main
```

כשיתבקש:
- **Username:** `5717101-stack`
- **Password:** הדבק את ה-Personal Access Token (לא את הסיסמה!)

## טיפים:

1. **שמור את ה-Token** - תצטרך אותו בעתיד
2. **אל תשתף את ה-Token** - זה כמו סיסמה
3. **אם שכחת** - תצטרך ליצור Token חדש

## אם עדיין לא עובד:

1. ודא שהעתקת את כל ה-Token (כולל `ghp_`)
2. ודא שסימנת את ה-scope `repo`
3. נסה ליצור Token חדש

## אלטרנטיבה: SSH (מתקדם יותר)

אם אתה רוצה, אפשר גם להשתמש ב-SSH במקום HTTPS:
1. צור SSH key
2. הוסף אותו ל-GitHub
3. שנה את ה-remote ל-SSH

אבל Personal Access Token הוא הכי פשוט!

