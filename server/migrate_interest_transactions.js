// Migration script to update existing interest transactions
// This script updates all interest transactions to have proper id format
// Run this once to fix historical data

import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';

async function migrateInterestTransactions() {
  let client;
  
  try {
    console.log('🔄 Starting interest transactions migration...');
    
    client = new MongoClient(MONGODB_URI);
    await client.connect();
    console.log('✅ Connected to MongoDB');
    
    const db = client.db();
    const familiesCollection = db.collection('families');
    
    // Find all families
    const families = await familiesCollection.find({}).toArray();
    console.log(`📊 Found ${families.length} families to process`);
    
    let totalUpdated = 0;
    let totalFamiliesUpdated = 0;
    
    for (const family of families) {
      if (!family.children || !Array.isArray(family.children)) continue;
      
      let familyUpdated = false;
      const updates = [];
      
      for (let i = 0; i < family.children.length; i++) {
        const child = family.children[i];
        if (!child.transactions || !Array.isArray(child.transactions)) continue;
        
        let childUpdated = false;
        const updatedTransactions = child.transactions.map(transaction => {
          // Check if this is an interest transaction that needs fixing
          // It should have description with "ריבית" or "interest" but id doesn't start with "interest_"
          const isInterestByDescription = transaction.description && 
            (transaction.description.includes('ריבית') || transaction.description.includes('interest'));
          
          const hasCorrectId = transaction.id && 
            typeof transaction.id === 'string' && 
            transaction.id.startsWith('interest_');
          
          // If it's an interest transaction but doesn't have correct id format, fix it
          if (isInterestByDescription && !hasCorrectId) {
            childUpdated = true;
            totalUpdated++;
            
            // Generate proper id format: interest_${timestamp}_${childId}
            const timestamp = transaction.date ? new Date(transaction.date).getTime() : Date.now();
            const childId = child._id || `child_${i}`;
            const newId = `interest_${timestamp}_${childId}`;
            
            console.log(`  📝 Updating transaction: ${transaction.id || 'no-id'} -> ${newId} (${transaction.description})`);
            
            return {
              ...transaction,
              id: newId
            };
          }
          
          return transaction;
        });
        
        if (childUpdated) {
          familyUpdated = true;
          updates.push({
            filter: { _id: family._id, 'children._id': child._id },
            update: { $set: { 'children.$.transactions': updatedTransactions } }
          });
        }
      }
      
      // Apply all updates for this family
      if (familyUpdated) {
        totalFamiliesUpdated++;
        for (const { filter, update } of updates) {
          await familiesCollection.updateOne(filter, update);
        }
        console.log(`✅ Updated family ${family._id} (${family.name || 'unnamed'})`);
      }
    }
    
    console.log('');
    console.log('✅ Migration complete!');
    console.log(`📊 Summary:`);
    console.log(`   - Families processed: ${families.length}`);
    console.log(`   - Families updated: ${totalFamiliesUpdated}`);
    console.log(`   - Transactions updated: ${totalUpdated}`);
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    throw error;
  } finally {
    if (client) {
      await client.close();
      console.log('🔌 Disconnected from MongoDB');
    }
  }
}

// Run migration if called directly
migrateInterestTransactions()
  .then(() => {
    console.log('✅ Migration completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  });
