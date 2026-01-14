#!/usr/bin/env node

/**
 * Delete paymentRequests field completely to fix timeout
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI;
const PROBLEMATIC_FAMILY_ID = 'family_1768251654358_2173y0h';

async function deletePaymentRequests() {
  let client;
  try {
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 120000,
      connectTimeoutMS: 30000,
    });
    await client.connect();
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    console.log('🔧 Removing paymentRequests field...\n');
    
    // Directly unset the field without reading it first
    console.log('   Attempting to unset paymentRequests field...');
    const result = await familiesCollection.updateOne(
      { _id: PROBLEMATIC_FAMILY_ID },
      { $unset: { paymentRequests: '' } }
    );
    
    if (result.modifiedCount > 0) {
      console.log('   ✅ Successfully removed paymentRequests field!');
      
      // Verify we can now load the family
      console.log('\n   Verifying fix...');
      const family = await familiesCollection.findOne({ _id: PROBLEMATIC_FAMILY_ID });
      if (family) {
        const size = JSON.stringify(family).length;
        console.log(`   ✅ Family can now be loaded! Size: ${(size / 1024).toFixed(2)} KB`);
        console.log(`   Children: ${family.children?.length || 0}`);
        console.log(`   Transactions: ${family.children?.reduce((sum, c) => sum + (c.transactions?.length || 0), 0) || 0}`);
      } else {
        console.log('   ❌ Family still cannot be loaded');
      }
    } else {
      console.log('   ⚠️  Field may not exist or already removed');
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    if (client) await client.close();
  }
}

deletePaymentRequests();
