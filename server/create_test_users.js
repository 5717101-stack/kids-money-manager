import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';

// Test phone numbers
const TEST_PHONE_NUMBERS = {
  PARENT: '+1123456789',
  CHILD: '+1123412345'
};

// Normalize phone number - same function as in server.js
function normalizePhoneNumber(phoneNumber, defaultCountryCode = '+972') {
  if (!phoneNumber) return phoneNumber;
  const trimmed = phoneNumber.trim();
  
  if (trimmed.startsWith('+')) {
    if (trimmed.startsWith('+9720') && trimmed.length > 5) {
      return '+972' + trimmed.substring(5);
    }
    return trimmed;
  }
  
  if (trimmed.startsWith('0')) {
    return defaultCountryCode + trimmed.substring(1);
  }
  
  return defaultCountryCode + trimmed;
}

async function createTestUsers() {
  console.log(`📋 MongoDB URI: ${MONGODB_URI ? MONGODB_URI.replace(/\/\/([^:]+):([^@]+)@/, '//***:***@') : 'NOT SET'}`);
  
  let client;
  try {
    console.log('🔌 Connecting to MongoDB...');
    client = new MongoClient(MONGODB_URI);
    await client.connect();
    console.log('✅ Connected to MongoDB');

    const db = client.db();
    const familiesCollection = db.collection('families');

    const normalizedParentPhone = normalizePhoneNumber(TEST_PHONE_NUMBERS.PARENT);
    const normalizedChildPhone = normalizePhoneNumber(TEST_PHONE_NUMBERS.CHILD);

    console.log(`\n📱 Creating test users:`);
    console.log(`   Parent: ${normalizedParentPhone}`);
    console.log(`   Child: ${normalizedChildPhone}`);

    // Check if parent family already exists
    let family = await familiesCollection.findOne({ phoneNumber: normalizedParentPhone });
    
    if (family) {
      console.log(`\n⚠️  Parent family already exists: ${family._id}`);
      
      // Check if child already exists
      const existingChild = family.children?.find(
        ch => ch.phoneNumber && normalizePhoneNumber(ch.phoneNumber) === normalizedChildPhone
      );
      
      if (existingChild) {
        console.log(`⚠️  Child already exists: ${existingChild.name} (${existingChild._id})`);
        console.log(`\n✅ Test users already exist. No changes needed.`);
        return;
      } else {
        // Add child to existing family
        console.log(`\n➕ Adding child to existing family...`);
        const childId = `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        const child = {
          _id: childId,
          name: 'ילד בדיקה',
          phoneNumber: normalizedChildPhone,
          balance: 0,
          cashBoxBalance: 0,
          profileImage: null,
          weeklyAllowance: 0,
          allowanceType: 'weekly',
          allowanceDay: 1,
          allowanceTime: '08:00',
          weeklyInterestRate: 0,
          lastAllowancePayment: null,
          lastInterestCalculation: null,
          totalInterestEarned: 0,
          transactions: [],
          createdAt: new Date().toISOString()
        };

        await familiesCollection.updateOne(
          { _id: family._id },
          { $push: { children: child } }
        );

        // Update categories to include new child
        if (family.categories && family.categories.length > 0) {
          for (const category of family.categories) {
            if (!category.activeFor.includes(childId)) {
              category.activeFor.push(childId);
            }
          }
          await familiesCollection.updateOne(
            { _id: family._id },
            { $set: { categories: family.categories } }
          );
        }

        console.log(`✅ Child added successfully: ${child.name} (${childId})`);
        console.log(`\n✅ Test users ready!`);
        return;
      }
    }

    // Create new family with parent
    console.log(`\n➕ Creating new parent family...`);
    const familyId = `family_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    
    const childId = `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const child = {
      _id: childId,
      name: 'ילד בדיקה',
      phoneNumber: normalizedChildPhone,
      balance: 0,
      cashBoxBalance: 0,
      profileImage: null,
      weeklyAllowance: 0,
      allowanceType: 'weekly',
      allowanceDay: 1,
      allowanceTime: '08:00',
      weeklyInterestRate: 0,
      lastAllowancePayment: null,
      lastInterestCalculation: null,
      totalInterestEarned: 0,
      transactions: [],
      createdAt: new Date().toISOString()
    };

    family = {
      _id: familyId,
      phoneNumber: normalizedParentPhone,
      parentName: 'הורה בדיקה',
      countryCode: '+1',
      createdAt: new Date().toISOString(),
      children: [child],
      categories: [
        { _id: 'cat_1', name: 'משחקים', activeFor: [childId] },
        { _id: 'cat_2', name: 'ממתקים', activeFor: [childId] },
        { _id: 'cat_3', name: 'בגדים', activeFor: [childId] },
        { _id: 'cat_4', name: 'בילויים', activeFor: [childId] },
        { _id: 'cat_5', name: 'אחר', activeFor: [childId] }
      ]
    };

    await familiesCollection.insertOne(family);
    console.log(`✅ Family created: ${familyId}`);
    console.log(`✅ Child created: ${child.name} (${childId})`);
    console.log(`\n✅ Test users created successfully!`);
    console.log(`\n📋 Summary:`);
    console.log(`   Family ID: ${familyId}`);
    console.log(`   Parent Phone: ${normalizedParentPhone}`);
    console.log(`   Child Name: ${child.name}`);
    console.log(`   Child Phone: ${normalizedChildPhone}`);
    console.log(`   Child ID: ${childId}`);

  } catch (error) {
    console.error('❌ Error creating test users:', error);
    process.exit(1);
  } finally {
    if (client) {
      await client.close();
      console.log('\n🔌 MongoDB connection closed');
    }
  }
}

// Run the script
createTestUsers()
  .then(() => {
    console.log('\n✨ Script completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\n❌ Script failed:', error);
    process.exit(1);
  });
