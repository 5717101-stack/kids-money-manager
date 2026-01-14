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
    console.log(`   URI: ${MONGODB_URI ? MONGODB_URI.replace(/\/\/([^:]+):([^@]+)@/, '//***:***@') : 'NOT SET'}`);
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000, // 30 seconds
      socketTimeoutMS: 60000, // 60 seconds
      connectTimeoutMS: 30000, // 30 seconds
    });
    await client.connect();
    const db = client.db();
    
    console.log('✅ Connected to MongoDB\n');
    
    // Check families collection
    console.log('📊 Checking families collection...');
    const familiesCollection = db.collection('families');
    const familyCount = await familiesCollection.countDocuments();
    console.log(`   Total families: ${familyCount}`);
    
    // Find large documents - load one by one to catch problematic ones
    console.log('\n🔍 Checking each family individually...');
    const familyIds = await familiesCollection.distinct('_id');
    console.log(`   Found ${familyIds.length} family IDs`);
    
    let largeDocs = [];
    let totalSize = 0;
    let problematicDocs = [];
    
    for (let i = 0; i < familyIds.length; i++) {
      const familyId = familyIds[i];
      try {
        console.log(`   [${i + 1}/${familyIds.length}] Loading family ${familyId}...`);
        const family = await familiesCollection.findOne({ _id: familyId });
        
        if (!family) {
          console.log(`      ⚠️  Family not found: ${familyId}`);
          continue;
        }
        
        // Check for circular references or problematic structures
        let docSize;
        try {
          docSize = JSON.stringify(family).length;
        } catch (stringifyError) {
          problematicDocs.push({
            _id: familyId,
            error: 'Cannot stringify - possible circular reference',
            errorMessage: stringifyError.message
          });
          console.log(`      ❌ Cannot stringify family ${familyId}: ${stringifyError.message}`);
          continue;
        }
        
        totalSize += docSize;
        
        // Count children and transactions
        const childrenCount = family.children?.length || 0;
        let transactionCount = 0;
        let maxChildTransactions = 0;
        
        if (family.children) {
          for (const child of family.children) {
            const childTxCount = child.transactions?.length || 0;
            transactionCount += childTxCount;
            if (childTxCount > maxChildTransactions) {
              maxChildTransactions = childTxCount;
            }
          }
        }
        
        console.log(`      ✅ Size: ${(docSize / 1024).toFixed(2)} KB, Children: ${childrenCount}, Transactions: ${transactionCount} (max per child: ${maxChildTransactions})`);
        
        if (docSize > 5 * 1024 * 1024) { // 5MB
          largeDocs.push({
            _id: familyId,
            size: (docSize / 1024 / 1024).toFixed(2) + ' MB',
            children: childrenCount,
            transactions: transactionCount,
            maxChildTransactions: maxChildTransactions
          });
        }
        
        // Check for suspiciously large transaction arrays
        if (maxChildTransactions > 10000) {
          problematicDocs.push({
            _id: familyId,
            warning: `Child has ${maxChildTransactions} transactions - might be corrupted`,
            children: childrenCount,
            transactions: transactionCount
          });
          console.log(`      ⚠️  WARNING: Child has ${maxChildTransactions} transactions!`);
        }
        
      } catch (error) {
        problematicDocs.push({
          _id: familyId,
          error: 'Error loading family',
          errorMessage: error.message
        });
        console.log(`      ❌ Error loading family ${familyId}: ${error.message}`);
      }
    }
    
    if (familyCount > 0) {
      console.log(`\n   Average document size: ${(totalSize / familyCount / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Total collection size: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
    }
    
    if (largeDocs.length > 0) {
      console.log(`\n⚠️  Found ${largeDocs.length} large documents (>5MB):`);
      largeDocs.forEach(doc => {
        console.log(`   - ${doc._id}: ${doc.size} (${doc.children} children, ${doc.transactions} transactions, max per child: ${doc.maxChildTransactions})`);
      });
    } else {
      console.log('\n   ✅ No large documents found');
    }
    
    if (problematicDocs.length > 0) {
      console.log(`\n🚨 Found ${problematicDocs.length} problematic documents:`);
      problematicDocs.forEach(doc => {
        console.log(`   - ${doc._id}:`);
        if (doc.error) {
          console.log(`     Error: ${doc.error}`);
          console.log(`     Message: ${doc.errorMessage}`);
        }
        if (doc.warning) {
          console.log(`     Warning: ${doc.warning}`);
          console.log(`     Children: ${doc.children}, Transactions: ${doc.transactions}`);
        }
      });
    }
    
    // Try to load problematic documents with projection (without transactions)
    if (problematicDocs.length > 0) {
      console.log(`\n🔧 Attempting to load problematic documents without transactions...`);
      for (const probDoc of problematicDocs) {
        try {
          console.log(`   Trying ${probDoc._id} with projection...`);
          const family = await familiesCollection.findOne(
            { _id: probDoc._id },
            {
              projection: {
                _id: 1,
                phoneNumber: 1,
                parentName: 1,
                createdAt: 1,
                children: {
                  _id: 1,
                  name: 1,
                  balance: 1,
                  // Exclude transactions
                  transactions: 0
                }
              }
            }
          );
          
          if (family) {
            const docSize = JSON.stringify(family).length;
            const childrenCount = family.children?.length || 0;
            console.log(`      ✅ Loaded without transactions: ${(docSize / 1024).toFixed(2)} KB, ${childrenCount} children`);
            console.log(`      💡 This family can be loaded with projection (excluding transactions)`);
          } else {
            console.log(`      ❌ Still cannot load even with projection`);
          }
        } catch (error) {
          console.log(`      ❌ Error even with projection: ${error.message}`);
        }
      }
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
