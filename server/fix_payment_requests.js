#!/usr/bin/env node

/**
 * Fix paymentRequests field in problematic family
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI;
const PROBLEMATIC_FAMILY_ID = 'family_1768251654358_2173y0h';

async function fixPaymentRequests() {
  let client;
  try {
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 60000,
    });
    await client.connect();
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    console.log('🔍 Checking paymentRequests field...\n');
    
    // Try to get paymentRequests count using aggregation
    const countResult = await familiesCollection.aggregate([
      { $match: { _id: PROBLEMATIC_FAMILY_ID } },
      { $project: { count: { $size: { $ifNull: ['$paymentRequests', []] } } } }
    ]).toArray();
    
    const count = countResult[0]?.count || 0;
    console.log(`   Payment requests count: ${count}`);
    
    if (count > 1000) {
      console.log(`   ⚠️  WARNING: ${count} payment requests - this is unusually high!`);
    }
    
    // Try to get first few payment requests to see structure
    console.log('\n📋 Attempting to get first payment request...');
    const firstRequest = await familiesCollection.aggregate([
      { $match: { _id: PROBLEMATIC_FAMILY_ID } },
      { $project: { firstRequest: { $arrayElemAt: ['$paymentRequests', 0] } } }
    ]).toArray();
    
    if (firstRequest[0]?.firstRequest) {
      const reqSize = JSON.stringify(firstRequest[0].firstRequest).length;
      console.log(`   First request size: ${(reqSize / 1024).toFixed(2)} KB`);
      console.log(`   Structure:`, Object.keys(firstRequest[0].firstRequest));
      
      // Check if there's a large image field
      if (firstRequest[0].firstRequest.image) {
        const imgSize = firstRequest[0].firstRequest.image.length;
        console.log(`   ⚠️  Image size: ${(imgSize / 1024 / 1024).toFixed(2)} MB`);
        if (imgSize > 5 * 1024 * 1024) {
          console.log(`   🚨 CRITICAL: Image is ${(imgSize / 1024 / 1024).toFixed(2)} MB - this is too large!`);
        }
      }
    }
    
    // Try to fix by removing large images from payment requests
    console.log('\n🔧 Attempting to fix by removing large images...');
    const family = await familiesCollection.findOne(
      { _id: PROBLEMATIC_FAMILY_ID },
      { projection: { paymentRequests: 1 } }
    );
    
    if (family && family.paymentRequests) {
      let fixed = false;
      const updatedRequests = family.paymentRequests.map(req => {
        if (req.image && req.image.length > 1024 * 1024) { // > 1MB
          console.log(`   Removing large image from request ${req._id} (${(req.image.length / 1024 / 1024).toFixed(2)} MB)`);
          fixed = true;
          return { ...req, image: null };
        }
        return req;
      });
      
      if (fixed) {
        console.log('   Updating family with fixed payment requests...');
        await familiesCollection.updateOne(
          { _id: PROBLEMATIC_FAMILY_ID },
          { $set: { paymentRequests: updatedRequests } }
        );
        console.log('   ✅ Fixed! Large images removed from payment requests.');
      } else {
        console.log('   No large images found in payment requests.');
      }
    }
    
    // Alternative: Try to unset paymentRequests if it's corrupted
    console.log('\n🔧 Testing if we can load family without paymentRequests...');
    const familyWithoutPR = await familiesCollection.findOne(
      { _id: PROBLEMATIC_FAMILY_ID },
      { projection: { paymentRequests: 0 } }
    );
    
    if (familyWithoutPR) {
      const size = JSON.stringify(familyWithoutPR).length;
      console.log(`   ✅ Can load without paymentRequests! Size: ${(size / 1024).toFixed(2)} KB`);
      console.log(`   💡 Recommendation: Clear or fix paymentRequests field`);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.message.includes('timeout')) {
      console.error('   🚨 Still timing out - paymentRequests field is severely corrupted');
      console.error('   💡 Recommendation: Unset paymentRequests field completely');
    }
  } finally {
    if (client) await client.close();
  }
}

fixPaymentRequests();
