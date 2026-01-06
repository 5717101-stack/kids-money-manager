# התקנת Node.js

Node.js נדרש להרצת הפרויקט. יש כמה דרכים להתקין:

## אופציה 1: הורדה ישירה (מומלץ)

1. גש ל: https://nodejs.org/
2. הורד את הגרסה LTS (Long Term Support)
3. התקן את הקובץ שהורדת
4. בדוק שההתקנה הצליחה:
   ```bash
   node --version
   npm --version
   ```

## אופציה 2: דרך Homebrew

אם יש לך Homebrew מותקן:
```bash
brew install node
```

## אופציה 3: דרך nvm (Node Version Manager)

```bash
# התקן nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# טען את nvm
source ~/.zshrc

# התקן Node.js
nvm install --lts
nvm use --lts
```

לאחר התקנת Node.js, הרץ:
```bash
cd ~/Projects/kids-money-manager
npm install
cd server
npm install
```
