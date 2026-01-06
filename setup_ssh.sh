#!/bin/bash
# סקריפט להגדרת SSH Key ל-GitHub

echo "=== הגדרת SSH Key ל-GitHub ==="
echo ""

# בדוק אם יש כבר SSH key
if [ -f ~/.ssh/github_kids_money ]; then
    echo "⚠️ SSH key כבר קיים: ~/.ssh/github_kids_money"
    read -p "להמשיך בכל זאת? (y/n): " continue
    if [ "$continue" != "y" ]; then
        exit 0
    fi
fi

# צור SSH key
echo "1. יוצר SSH key..."
ssh-keygen -t ed25519 -C "kids-money-manager" -f ~/.ssh/github_kids_money -N ""

if [ $? -ne 0 ]; then
    echo "❌ שגיאה ביצירת SSH key"
    exit 1
fi

echo ""
echo "✅ SSH key נוצר!"
echo ""

# הצג את ה-public key
echo "2. Public Key שלך:"
echo "---"
cat ~/.ssh/github_kids_money.pub
echo "---"
echo ""

# הוסף ל-SSH config
echo "3. מוסיף ל-SSH config..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

cat >> ~/.ssh/config << 'SSHCONFIG'

Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_kids_money
  IdentitiesOnly yes
SSHCONFIG

chmod 600 ~/.ssh/config

echo "✅ SSH config עודכן"
echo ""

# שנה את ה-remote URL
echo "4. משנה את ה-remote URL ל-SSH..."
cd ~/Projects/kids-money-manager
git remote set-url origin git@github.com:5717101-stack/kids-money-manager.git

echo "✅ Remote URL עודכן"
echo ""

echo "=== שלבים הבאים ==="
echo ""
echo "1. העתק את ה-Public Key למעלה"
echo "2. לך ל: https://github.com/settings/keys"
echo "3. לחץ 'New SSH key'"
echo "4. תן שם: 'Kids Money Manager'"
echo "5. הדבק את ה-Key ולחץ 'Add SSH key'"
echo ""
echo "6. אחרי שתסיים, הרץ:"
echo "   ssh -T git@github.com"
echo "   (אמור לומר: Hi 5717101-stack! You've successfully authenticated...)"
echo ""
echo "7. נסה push:"
echo "   git push origin main"
echo ""
