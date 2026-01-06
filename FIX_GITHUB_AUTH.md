# תיקון בעיית Authentication ב-GitHub

## הבעיה:
GitHub לא תומך יותר ב-password authentication. צריך Personal Access Token.

## פתרון מהיר:

### שלב 1: צור Personal Access Token

1. לך ל: https://github.com/settings/tokens
2. לחץ "Generate new token" → "Generate new token (classic)"
3. תן שם: `kids-money-manager-push`
4. בחר permissions:
   - ✅ `repo` (כל ה-sub-permissions)
5. לחץ "Generate token"
6. **העתק את ה-Token מיד!** (תראה אותו רק פעם אחת)

### שלב 2: השתמש ב-Token

**אפשרות 1: דרך URL (הכי פשוט)**
```bash
cd ~/Projects/kids-money-manager
git remote set-url origin https://YOUR_TOKEN@github.com/5717101-stack/kids-money-manager.git
git push origin main
```

**אפשרות 2: דרך credential helper**
```bash
cd ~/Projects/kids-money-manager
git push origin main
# כשמבקשים username: הכנס את ה-username שלך
# כשמבקשים password: הכנס את ה-Token (לא את הסיסמה!)
```

**אפשרות 3: שמור ב-credential helper**
```bash
cd ~/Projects/kids-money-manager
git config --global credential.helper osxkeychain
git push origin main
# הכנס username ו-token - זה יישמר ב-keychain
```

### שלב 3: בדיקה

אחרי ה-push:
- לך ל-GitHub → תראה את ה-commit החדש
- Vercel יעשה deploy אוטומטי
- Railway יעשה deploy אוטומטי

## הערות:

- Token תקף עד שתמחק אותו
- אפשר ליצור token חדש בכל עת
- Token עם permission `repo` מאפשר push/pull
