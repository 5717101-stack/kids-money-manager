# הגדרת Push אוטומטי ל-GitHub

## הבעיה:
Git לא יכול לדחוף אוטומטית כי צריך credentials אינטראקטיביים.

## פתרונות להגדרה:

### אופציה 1: Personal Access Token ב-Keychain (מומלץ)

**שלב 1: צור Token**
1. לך ל: https://github.com/settings/tokens
2. לחץ "Generate new token (classic)"
3. תן שם: `kids-money-manager-auto-push`
4. בחר permission: `repo` (כל ה-sub-permissions)
5. לחץ "Generate token"
6. **העתק את ה-Token מיד!**

**שלב 2: שמור ב-Keychain**
```bash
cd ~/Projects/kids-money-manager
git push origin main
# כשמבקשים username: הכנס את ה-username שלך
# כשמבקשים password: הכנס את ה-Token (לא את הסיסמה!)
```

זה יישמר ב-Keychain ויעבוד גם בעתיד.

**שלב 3: בדיקה**
```bash
git push origin main
# אמור לעבוד בלי לבקש credentials
```

---

### אופציה 2: SSH Key (הכי בטוח)

**שלב 1: צור SSH Key**
```bash
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/github_kids_money
# לחץ Enter לכל השאלות (או תן passphrase אם תרצה)
```

**שלב 2: הוסף ל-GitHub**
```bash
cat ~/.ssh/github_kids_money.pub
# העתק את התוכן
```

1. לך ל: https://github.com/settings/keys
2. לחץ "New SSH key"
3. תן שם: `Kids Money Manager`
4. הדבק את ה-Key
5. לחץ "Add SSH key"

**שלב 3: הגדר Git להשתמש ב-SSH**
```bash
cd ~/Projects/kids-money-manager
git remote set-url origin git@github.com:5717101-stack/kids-money-manager.git
```

**שלב 4: הוסף ל-SSH config**
```bash
cat >> ~/.ssh/config << 'SSHCONFIG'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_kids_money
  IdentitiesOnly yes
SSHCONFIG

chmod 600 ~/.ssh/config
```

**שלב 5: בדיקה**
```bash
ssh -T git@github.com
# אמור לומר: "Hi 5717101-stack! You've successfully authenticated..."

git push origin main
# אמור לעבוד בלי credentials!
```

---

### אופציה 3: GitHub CLI (gh)

**שלב 1: התקן GitHub CLI**
```bash
brew install gh
```

**שלב 2: התחבר**
```bash
gh auth login
# בחר GitHub.com
# בחר HTTPS
# בחר "Login with a web browser"
# התחבר בדפדפן
```

**שלב 3: בדיקה**
```bash
gh auth status
# אמור להראות שאתה מחובר

git push origin main
# אמור לעבוד!
```

---

## איזה אופציה לבחור?

- **אופציה 1 (Token ב-Keychain)**: הכי פשוט, אבל לא תמיד עובד ב-non-interactive
- **אופציה 2 (SSH)**: הכי בטוח ויציב, עובד תמיד
- **אופציה 3 (GitHub CLI)**: טוב אם אתה משתמש ב-gh גם לדברים אחרים

## המלצה: אופציה 2 (SSH)

SSH הוא הכי בטוח ויציב, ועובד גם ב-non-interactive mode.

---

## אחרי ההגדרה:

אחרי שתגדיר אחת מהאופציות, אני אוכל לדחוף אוטומטית בעתיד!

נסה עכשיו:
```bash
git push origin main
```

אם זה עובד בלי לבקש credentials, הכל מוכן! ✅
