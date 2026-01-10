#!/bin/bash

# Script to fix Xcode Capacitor package issues

echo "Cleaning Xcode caches..."

# Clean DerivedData
rm -rf ~/Library/Developer/Xcode/DerivedData/*

# Clean Swift PM cache
rm -rf ~/Library/Caches/org.swift.swiftpm

# Clean local Swift PM
cd ios/App
rm -rf .swiftpm

echo "Caches cleaned. Now:"
echo "1. Open Xcode: open ios/App/App.xcodeproj"
echo "2. Go to File → Packages → Reset Package Caches"
echo "3. Go to File → Packages → Resolve Package Versions"
echo "4. Wait for packages to download"
echo "5. Build the project (Cmd+B)"
