#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

echo "Installing Node.js 22..."
nvm install 22
nvm use 22
nvm alias default 22

echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"

cd /Users/itzhakbachar/Projects/kids-money-manager
echo "Installing dependencies..."
npm install

echo "Syncing Capacitor..."
npx cap sync ios

echo "Building project..."
npm run build

echo "Copying files to iOS..."
rm -rf ios/App/App/public/assets ios/App/App/public/index.html
cp -r dist/assets ios/App/App/public/
cp dist/index.html ios/App/App/public/

echo "Done! Now open Xcode and:"
echo "1. File → Packages → Reset Package Caches"
echo "2. File → Packages → Resolve Package Versions"
echo "3. Product → Clean Build Folder (Shift+Cmd+K)"
echo "4. Product → Build (Cmd+B)"
