#!/usr/bin/env node

/**
 * Check specific fields in problematic family
 */

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI;
const PROBLEMATIC_FAMILY_ID = 'family_1768251654358_2173y0h';

async function checkFields() {
  let client;
  try {
    client = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 60000,
    });
    await client.connect();
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    console.log('🔍 Checking individual fields...\n');
    
    // Check each field separately
    const fieldsToCheck = [
      { field: '_id', projection: { _id: 1 } },
      { field: 'phoneNumber', projection: { _id: 1, phoneNumber: 1 } },
      { field: 'parentName', projection: { _id: 1, parentName: 1 } },
      { field: 'parentProfileImage', projection: { _id: 1, parentProfileImage: 1 } },
      { field: 'children (basic)', projection: { _id: 1, 'children._id': 1, 'children.name': 1 } },
      { field: 'children.profileImage', projection: { _id: 1, 'children.profileImage': 1 } },
      { field: 'children.transactions', projection: { _id: 1, 'children.transactions': 1 } },
      { field: 'categories', projection: { _id: 1, categories: 1 } },
      { field: 'paymentRequests', projection: { _id: 1, paymentRequests: 1 } },
    ];
    
    for (const { field, projection } of fieldsToCheck) {
      try {
        console.log(`Checking ${field}...`);
        const start = Date.now();
        const result = await familiesCollection.findOne(
          { _id: PROBLEMATIC_FAMILY_ID },
          { projection }
        );
        const duration = Date.now() - start;
        
        if (result) {
          const size = JSON.stringify(result).length;
          console.log(`   ✅ Loaded in ${duration}ms, size: ${(size / 1024).toFixed(2)} KB`);
          
          // Check for suspiciously large fields
          if (field === 'parentProfileImage' && result.parentProfileImage) {
            const imgSize = result.parentProfileImage.length;
            console.log(`   ⚠️  Profile image size: ${(imgSize / 1024 / 1024).toFixed(2)} MB`);
          }
          
          if (field === 'children.profileImage' && result.children) {
            result.children.forEach((child, idx) => {
              if (child.profileImage) {
                const imgSize = child.profileImage.length;
                console.log(`   ⚠️  Child ${idx + 1} profile image: ${(imgSize / 1024 / 1024).toFixed(2)} MB`);
              }
            });
          }
          
          if (field === 'children.transactions' && result.children) {
            result.children.forEach((child, idx) => {
              const txCount = child.transactions?.length || 0;
              if (txCount > 0) {
                const txSize = JSON.stringify(child.transactions).length;
                console.log(`   Child ${idx + 1} transactions: ${txCount} transactions, ${(txSize / 1024).toFixed(2)} KB`);
              }
            });
          }
        } else {
          console.log(`   ❌ Not found`);
        }
      } catch (error) {
        console.log(`   ❌ Error: ${error.message}`);
        if (error.message.includes('timeout')) {
          console.log(`   🚨 TIMEOUT on field: ${field}`);
          console.log(`   💡 This field is likely causing the problem!`);
        }
      }
      console.log('');
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    if (client) await client.close();
  }
}

checkFields();
