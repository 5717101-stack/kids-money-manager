#!/usr/bin/env node

/**
 * Database Health Check Script
 * Checks for large documents and potential issues in MongoDB
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';

async function checkDatabase() {
  let client;
  try {
    console.log('🔍 Connecting to MongoDB...');
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    });
    await client.connect();
    const db = client.db();
    
    console.log('✅ Connected to MongoDB\n');
    
    // Check families collection
    console.log('📊 Checking families collection...');
    const familiesCollection = db.collection('families');
    const familyCount = await familiesCollection.countDocuments();
    console.log(`   Total families: ${familyCount}`);
    
    // Find large documents
    console.log('\n🔍 Checking for large documents...');
    const families = await familiesCollection.find({}).toArray();
    
    let largeDocs = [];
    let totalSize = 0;
    
    for (const family of families) {
      const docSize = JSON.stringify(family).length;
      totalSize += docSize;
      
      if (docSize > 5 * 1024 * 1024) { // 5MB
        largeDocs.push({
          _id: family._id,
          size: (docSize / 1024 / 1024).toFixed(2) + ' MB',
          children: family.children?.length || 0,
          transactions: family.children?.reduce((sum, c) => sum + (c.transactions?.length || 0), 0) || 0
        });
      }
    }
    
    console.log(`   Average document size: ${(totalSize / familyCount / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   Total collection size: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
    
    if (largeDocs.length > 0) {
      console.log(`\n⚠️  Found ${largeDocs.length} large documents (>5MB):`);
      largeDocs.forEach(doc => {
        console.log(`   - ${doc._id}: ${doc.size} (${doc.children} children, ${doc.transactions} transactions)`);
      });
    } else {
      console.log('   ✅ No large documents found');
    }
    
    // Check for documents approaching 16MB limit
    const veryLargeDocs = families.filter(f => {
      const size = JSON.stringify(f).length;
      return size > 15 * 1024 * 1024; // 15MB
    });
    
    if (veryLargeDocs.length > 0) {
      console.log(`\n🚨 CRITICAL: Found ${veryLargeDocs.length} documents approaching 16MB limit:`);
      veryLargeDocs.forEach(f => {
        const size = JSON.stringify(f).length;
        console.log(`   - ${f._id}: ${(size / 1024 / 1024).toFixed(2)} MB`);
      });
      console.log('\n   ⚠️  These documents may cause loading issues!');
    }
    
    // Check indexes
    console.log('\n📇 Checking indexes...');
    const indexes = await familiesCollection.indexes();
    console.log(`   Total indexes: ${indexes.length}`);
    indexes.forEach(idx => {
      console.log(`   - ${idx.name}: ${JSON.stringify(idx.key)}`);
    });
    
    console.log('\n✅ Database check complete!');
    
  } catch (error) {
    console.error('❌ Error checking database:', error.message);
    process.exit(1);
  } finally {
    if (client) {
      await client.close();
      console.log('\n🔌 Disconnected from MongoDB');
    }
  }
}

checkDatabase();
