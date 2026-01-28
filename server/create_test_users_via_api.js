// Alternative script to create test users via API
// This can work if you have access to the production server

const TEST_PHONE_NUMBERS = {
  PARENT: '+1123456789',
  CHILD: '+1123412345'
};

async function createTestUsersViaAPI() {
  const API_URL = process.env.API_URL || 'https://kids-money-manager-server.onrender.com/api';
  
  console.log('📋 Creating test users via API...');
  console.log(`   API URL: ${API_URL}`);
  console.log(`   Parent: ${TEST_PHONE_NUMBERS.PARENT}`);
  console.log(`   Child: ${TEST_PHONE_NUMBERS.CHILD}`);
  
  try {
    // Step 1: Send OTP for parent (will be bypassed for test numbers)
    console.log('\n📤 Step 1: Sending OTP for parent...');
    const parentOTPResponse = await fetch(`${API_URL}/auth/send-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phoneNumber: TEST_PHONE_NUMBERS.PARENT })
    });
    
    if (!parentOTPResponse.ok) {
      const error = await parentOTPResponse.json();
      throw new Error(error.error || 'Failed to send OTP for parent');
    }
    
    console.log('✅ Parent OTP sent (bypassed for test number)');
    
    // Step 2: Verify OTP for parent (will be bypassed)
    console.log('\n📤 Step 2: Verifying OTP for parent...');
    const parentVerifyResponse = await fetch(`${API_URL}/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        phoneNumber: TEST_PHONE_NUMBERS.PARENT,
        otpCode: '123456' // Fake OTP for test numbers
      })
    });
    
    if (!parentVerifyResponse.ok) {
      const error = await parentVerifyResponse.json();
      throw new Error(error.error || 'Failed to verify OTP for parent');
    }
    
    const parentData = await parentVerifyResponse.json();
    console.log('✅ Parent verified and logged in');
    console.log(`   Family ID: ${parentData.familyId}`);
    
    // Step 3: Add child to the family
    if (parentData.familyId) {
      console.log('\n📤 Step 3: Adding child to family...');
      const addChildResponse = await fetch(`${API_URL}/families/${parentData.familyId}/children`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'ילד בדיקה',
          phoneNumber: TEST_PHONE_NUMBERS.CHILD
        })
      });
      
      if (!addChildResponse.ok) {
        const error = await addChildResponse.json();
        // If child already exists, that's okay
        if (error.error && error.error.includes('כבר בשימוש')) {
          console.log('⚠️  Child already exists (this is okay)');
        } else {
          throw new Error(error.error || 'Failed to add child');
        }
      } else {
        const childData = await addChildResponse.json();
        console.log('✅ Child added successfully');
        console.log(`   Child ID: ${childData.childId}`);
      }
    }
    
    console.log('\n✅ Test users created successfully via API!');
    console.log('\n📋 Summary:');
    console.log(`   Family ID: ${parentData.familyId}`);
    console.log(`   Parent Phone: ${TEST_PHONE_NUMBERS.PARENT}`);
    console.log(`   Child Phone: ${TEST_PHONE_NUMBERS.CHILD}`);
    
  } catch (error) {
    console.error('\n❌ Error creating test users:', error.message);
    process.exit(1);
  }
}

// Run the script
createTestUsersViaAPI()
  .then(() => {
    console.log('\n✨ Script completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\n❌ Script failed:', error);
    process.exit(1);
  });
