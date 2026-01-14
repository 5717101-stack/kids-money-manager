#!/usr/bin/env node

/**
 * Remove large images from paymentRequests to fix timeout issue
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI;
const PROBLEMATIC_FAMILY_ID = 'family_1768251654358_2173y0h';

async function removeLargeImages() {
  let client;
  try {
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 120000, // 2 minutes for update
      connectTimeoutMS: 30000,
    });
    await client.connect();
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    console.log('🔧 Fixing paymentRequests by removing images...\n');
    
    // Use aggregation to get paymentRequests without loading the whole document
    const paymentRequests = await familiesCollection.aggregate([
      { $match: { _id: PROBLEMATIC_FAMILY_ID } },
      { $project: { paymentRequests: 1 } }
    ]).toArray();
    
    if (!paymentRequests[0] || !paymentRequests[0].paymentRequests) {
      console.log('   No payment requests found');
      return;
    }
    
    console.log(`   Found ${paymentRequests[0].paymentRequests.length} payment requests`);
    
    // Update each payment request to remove images
    const updatedRequests = paymentRequests[0].paymentRequests.map((req, idx) => {
      if (req.image) {
        const imgSize = req.image.length;
        console.log(`   Request ${idx + 1}: Removing image (${(imgSize / 1024 / 1024).toFixed(2)} MB)`);
        return { ...req, image: null };
      }
      return req;
    });
    
    // Update the family document
    console.log('\n   Updating family document...');
    const result = await familiesCollection.updateOne(
      { _id: PROBLEMATIC_FAMILY_ID },
      { $set: { paymentRequests: updatedRequests } }
    );
    
    if (result.modifiedCount > 0) {
      console.log('   ✅ Successfully removed images from payment requests!');
      
      // Verify we can now load the family
      console.log('\n   Verifying fix...');
      const family = await familiesCollection.findOne({ _id: PROBLEMATIC_FAMILY_ID });
      if (family) {
        const size = JSON.stringify(family).length;
        console.log(`   ✅ Family can now be loaded! Size: ${(size / 1024).toFixed(2)} KB`);
      }
    } else {
      console.log('   ⚠️  No changes made');
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    
    // If update fails, try to unset paymentRequests completely
    if (error.message.includes('timeout')) {
      console.log('\n   🔧 Attempting alternative fix: removing paymentRequests field entirely...');
      try {
        const result = await familiesCollection.updateOne(
          { _id: PROBLEMATIC_FAMILY_ID },
          { $unset: { paymentRequests: '' } }
        );
        if (result.modifiedCount > 0) {
          console.log('   ✅ Removed paymentRequests field entirely');
        }
      } catch (unsetError) {
        console.error('   ❌ Failed to remove paymentRequests:', unsetError.message);
      }
    }
  } finally {
    if (client) await client.close();
  }
}

removeLargeImages();
