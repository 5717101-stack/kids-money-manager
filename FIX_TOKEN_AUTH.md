# תיקון בעיית Token Authentication

## הבעיה:
GitHub לא מקבל את ה-Token כי הוא מנסה להשתמש ב-password authentication.

## פתרון: השתמש ב-Token דרך URL

### שלב 1: צור Token (אם עוד לא)
1. לך ל: https://github.com/settings/tokens
2. לחץ "Generate new token (classic)"
3. תן שם: `kids-money-manager-auto-push`
4. בחר permission: `repo` (כל ה-sub-permissions)
5. לחץ "Generate token"
6. **העתק את ה-Token מיד!**

### שלב 2: השתמש ב-Token דרך URL

**דרך 1: דרך URL (פעם אחת)**
```bash
cd ~/Projects/kids-money-manager
git remote set-url origin https://YOUR_TOKEN@github.com/5717101-stack/kids-money-manager.git
git push origin main
```

**דרך 2: דרך credential helper (נשמר ב-Keychain)**
```bash
cd ~/Projects/kids-money-manager

# שנה את ה-URL זמנית
git remote set-url origin https://YOUR_TOKEN@github.com/5717101-stack/kids-money-manager.git

# דחוף (זה יישמר ב-Keychain)
git push origin main

# החזר את ה-URL הרגיל (ללא Token)
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git

# עכשיו זה יעבוד מהקייchain
git push origin main
```

**דרך 3: דרך credential store (נשמר בקובץ)**
```bash
cd ~/Projects/kids-money-manager

# הגדר credential store
git config credential.helper store

# דחוף עם Token
git remote set-url origin https://YOUR_TOKEN@github.com/5717101-stack/kids-money-manager.git
git push origin main

# החזר את ה-URL
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git

# עכשיו זה יעבוד מהקובץ
git push origin main
```

## ⚠️ הערה חשובה:
החלף `YOUR_TOKEN` ב-Token האמיתי שלך!

## 💡 המלצה:
אופציה 2 (SSH) יותר בטוחה וקלה - הרץ: `./setup_ssh.sh`
