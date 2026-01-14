#!/usr/bin/env node

/**
 * Fix problematic family document
 * Attempts to load and repair a family that causes timeout
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';
const PROBLEMATIC_FAMILY_ID = 'family_1768251654358_2173y0h';

async function fixFamily() {
  let client;
  try {
    console.log('🔍 Connecting to MongoDB...');
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 60000,
      connectTimeoutMS: 30000,
    });
    await client.connect();
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    console.log('✅ Connected to MongoDB\n');
    
    // Try to get basic info only
    console.log('📋 Attempting to get basic family info...');
    const basicInfo = await familiesCollection.findOne(
      { _id: PROBLEMATIC_FAMILY_ID },
      {
        projection: {
          _id: 1,
          phoneNumber: 1,
          parentName: 1,
          createdAt: 1,
          'children._id': 1,
          'children.name': 1
        }
      }
    );
    
    if (basicInfo) {
      console.log('✅ Basic info loaded:');
      console.log(`   ID: ${basicInfo._id}`);
      console.log(`   Phone: ${basicInfo.phoneNumber}`);
      console.log(`   Parent: ${basicInfo.parentName || 'N/A'}`);
      console.log(`   Children count: ${basicInfo.children?.length || 0}`);
      
      if (basicInfo.children) {
        basicInfo.children.forEach((child, idx) => {
          console.log(`   Child ${idx + 1}: ${child.name} (${child._id})`);
        });
      }
    } else {
      console.log('❌ Family not found');
      return;
    }
    
    // Try to count transactions using aggregation
    console.log('\n📊 Counting transactions using aggregation...');
    const transactionCount = await familiesCollection.aggregate([
      { $match: { _id: PROBLEMATIC_FAMILY_ID } },
      { $unwind: { path: '$children', preserveNullAndEmptyArrays: true } },
      { $unwind: { path: '$children.transactions', preserveNullAndEmptyArrays: true } },
      { $count: 'total' }
    ]).toArray();
    
    console.log(`   Total transactions: ${transactionCount[0]?.total || 0}`);
    
    // Try to get transaction count per child
    console.log('\n📊 Getting transaction count per child...');
    const childTxCounts = await familiesCollection.aggregate([
      { $match: { _id: PROBLEMATIC_FAMILY_ID } },
      { $unwind: { path: '$children', preserveNullAndEmptyArrays: true } },
      {
        $project: {
          childId: '$children._id',
          childName: '$children.name',
          transactionCount: { $size: { $ifNull: ['$children.transactions', []] } }
        }
      }
    ]).toArray();
    
    console.log('   Transaction counts per child:');
    childTxCounts.forEach(child => {
      console.log(`   - ${child.childName} (${child.childId}): ${child.transactionCount} transactions`);
      if (child.transactionCount > 1000) {
        console.log(`     ⚠️  WARNING: This child has ${child.transactionCount} transactions!`);
      }
    });
    
    // Try to load with limit on transactions
    console.log('\n🔧 Attempting to load family with limited transactions...');
    const familyWithLimitedTx = await familiesCollection.findOne(
      { _id: PROBLEMATIC_FAMILY_ID }
    );
    
    if (familyWithLimitedTx) {
      // Count actual transactions
      let totalTx = 0;
      let maxTx = 0;
      if (familyWithLimitedTx.children) {
        familyWithLimitedTx.children.forEach(child => {
          const txCount = child.transactions?.length || 0;
          totalTx += txCount;
          if (txCount > maxTx) maxTx = txCount;
        });
      }
      
      const docSize = JSON.stringify(familyWithLimitedTx).length;
      console.log(`   ✅ Loaded successfully!`);
      console.log(`   Document size: ${(docSize / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Total transactions: ${totalTx}`);
      console.log(`   Max transactions per child: ${maxTx}`);
      
      if (docSize > 15 * 1024 * 1024) {
        console.log(`\n   🚨 CRITICAL: Document is ${(docSize / 1024 / 1024).toFixed(2)} MB - approaching 16MB limit!`);
        console.log(`   💡 Recommendation: Archive old transactions or split into separate collection`);
      }
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('   Stack:', error.stack);
  } finally {
    if (client) {
      await client.close();
      console.log('\n🔌 Disconnected from MongoDB');
    }
  }
}

fixFamily();
