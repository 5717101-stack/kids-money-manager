#!/bin/bash
# בדיקת יכולת Push אוטומטי

cd ~/Projects/kids-money-manager

echo "=== בדיקת יכולת Push אוטומטי ==="
echo ""

# בדוק אם יש commits לדחיפה
COMMITS_TO_PUSH=$(git log origin/main..HEAD --oneline 2>&1 | wc -l | tr -d ' ')

if [ "$COMMITS_TO_PUSH" = "0" ]; then
    echo "✅ אין commits חדשים לדחיפה"
    echo "   הכל מעודכן ב-GitHub"
    exit 0
fi

echo "📤 יש $COMMITS_TO_PUSH commits לדחיפה:"
git log origin/main..HEAD --oneline
echo ""

# נסה push
echo "מנסה לדחוף..."
if git push origin main 2>&1; then
    echo ""
    echo "✅ Push הצליח! אני יכול לדחוף אוטומטית!"
else
    echo ""
    echo "❌ Push נכשל - עדיין צריך credentials"
    echo ""
    echo "💡 פתרון: עבור ל-SSH"
    echo "   ./setup_ssh.sh"
fi
