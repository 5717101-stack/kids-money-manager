#!/bin/bash

# Script to migrate existing interest transactions in the database
# This updates all interest transactions to have proper id format

echo "🔄 Starting interest transactions migration..."
echo ""

# Check if MONGODB_URI is set
if [ -z "$MONGODB_URI" ]; then
    echo "⚠️  MONGODB_URI environment variable not set"
    echo "Please set it before running:"
    echo "  export MONGODB_URI='your-mongodb-connection-string'"
    echo ""
    echo "Or run from server directory where .env might be loaded:"
    echo "  cd server && node migrate_interest_transactions.js"
    exit 1
fi

# Run the migration
cd "$(dirname "$0")"
node migrate_interest_transactions.js
