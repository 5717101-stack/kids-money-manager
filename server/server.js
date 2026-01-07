import express from 'express';
import cors from 'cors';
import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import crypto from 'crypto';
import twilio from 'twilio';

dotenv.config();

// Get version from package.json
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageJson = JSON.parse(readFileSync(join(__dirname, 'package.json'), 'utf8'));
const VERSION = packageJson.version;

// Log version at startup
console.log(`\n=== Kids Money Manager Server ===`);
console.log(`Version: ${VERSION}`);
console.log(`Starting...\n`);

const app = express();
const PORT = process.env.PORT || 3001;

// Twilio configuration (for SMS OTP)
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER;
let twilioClient = null;

// Log Twilio configuration on startup
console.log(`\n=== Twilio Configuration ===`);
console.log(`[TWILIO] Account SID: ${TWILIO_ACCOUNT_SID ? `${TWILIO_ACCOUNT_SID.substring(0, 10)}...${TWILIO_ACCOUNT_SID.substring(TWILIO_ACCOUNT_SID.length - 4)}` : 'NOT SET'}`);
console.log(`[TWILIO] Auth Token: ${TWILIO_AUTH_TOKEN ? `${TWILIO_AUTH_TOKEN.substring(0, 10)}...${TWILIO_AUTH_TOKEN.substring(TWILIO_AUTH_TOKEN.length - 4)}` : 'NOT SET'}`);
console.log(`[TWILIO] Phone Number: ${TWILIO_PHONE_NUMBER || 'NOT SET'}`);
console.log(`[TWILIO] Client Status: ${(TWILIO_ACCOUNT_SID && TWILIO_AUTH_TOKEN && TWILIO_PHONE_NUMBER) ? 'READY' : 'NOT CONFIGURED'}`);

if (TWILIO_ACCOUNT_SID && TWILIO_AUTH_TOKEN && TWILIO_PHONE_NUMBER) {
  try {
    twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
    console.log(`[TWILIO] ✅ Client initialized successfully`);
    console.log(`[TWILIO] From Number: ${TWILIO_PHONE_NUMBER}`);
    console.log(`[TWILIO] API Base URL: https://api.twilio.com`);
  } catch (error) {
    console.error(`[TWILIO] ❌ Failed to initialize: ${error.message}`);
  }
} else {
  console.log(`[TWILIO] ⚠️  Not configured - SMS will not be sent`);
  if (!TWILIO_ACCOUNT_SID) console.log(`[TWILIO]   Missing: TWILIO_ACCOUNT_SID`);
  if (!TWILIO_AUTH_TOKEN) console.log(`[TWILIO]   Missing: TWILIO_AUTH_TOKEN`);
  if (!TWILIO_PHONE_NUMBER) console.log(`[TWILIO]   Missing: TWILIO_PHONE_NUMBER`);
}
console.log(`===========================\n`);

// CRITICAL: Health check MUST be defined BEFORE any middleware
// Railway checks this immediately and if it's slow, container stops
// This endpoint must respond IMMEDIATELY - no logging, no processing
let serverReady = false;

// Health check endpoint - must be fastest possible
// Railway checks this endpoint to determine if service is healthy
// CRITICAL: This MUST respond immediately - Railway uses this to keep container alive
// MUST be defined BEFORE middleware to ensure fastest response
// NO LOGGING - any delay will cause Railway to kill the container
let healthCheckCount = 0;
let lastHealthCheckTime = Date.now();
app.get('/health', (req, res) => {
  healthCheckCount++;
  lastHealthCheckTime = Date.now();
  // NO LOGGING HERE - respond immediately
  // Railway needs instant 200 OK response
  res.status(200).json({ 
    status: 'ok'
  });
});

// Also add root endpoint that responds immediately
app.get('/', (req, res) => {
  res.status(200).json({ 
    message: 'Kids Money Manager API',
    status: 'running',
    version: VERSION,
    health: '/health',
    timestamp: new Date().toISOString()
  });
});

// Also respond to /api/health for compatibility
// NO LOGGING - respond immediately
app.get('/api/health', (req, res) => {
  healthCheckCount++;
  lastHealthCheckTime = Date.now();
  // NO LOGGING - respond immediately
  res.status(200).json({ 
    status: 'ok'
  });
});

// Middleware - CORS configuration
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));

// Logging middleware - only log important requests
app.use((req, res, next) => {
  // Only log API requests, not health checks
  if (req.path.startsWith('/api/') && req.path !== '/api/health') {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  }
  next();
});

// Keep-alive endpoint - Railway can use this to verify service is running
app.get('/keepalive', (req, res) => {
  res.status(200).json({ 
    status: 'alive', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: VERSION
  });
});

// MongoDB connection
let db;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';

async function connectDB() {
  try {
    const client = new MongoClient(MONGODB_URI);
    await client.connect();
    db = client.db();
    console.log('[DB] Connected to MongoDB');
    await initializeData();
  } catch (error) {
    console.error('[DB] Connection error:', error.message);
    console.log('[DB] Using in-memory storage');
  }
}

// Generate OTP code
function generateOTP() {
  return Math.floor(100000 + Math.random() * 900000).toString(); // 6-digit code
}

// Generate child join code
function generateChildCode() {
  return Math.random().toString(36).substring(2, 8).toUpperCase(); // 6-character code
}

// Send SMS via Twilio or log to console
async function sendSMS(phoneNumber, message) {
  const startTime = Date.now();
  console.log(`\n[SMS] ===== SMS Send Attempt =====`);
  console.log(`[SMS] Timestamp: ${new Date().toISOString()}`);
  console.log(`[SMS] To: ${phoneNumber}`);
  console.log(`[SMS] From: ${TWILIO_PHONE_NUMBER || 'NOT SET'}`);
  console.log(`[SMS] Message Length: ${message.length} characters`);
  console.log(`[SMS] Message Preview: ${message.substring(0, 50)}...`);
  console.log(`[SMS] Twilio Client: ${twilioClient ? 'INITIALIZED' : 'NOT INITIALIZED'}`);
  console.log(`[SMS] API Endpoint: https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID?.substring(0, 10)}.../Messages.json`);
  
  if (twilioClient && TWILIO_PHONE_NUMBER) {
    try {
      const requestPayload = {
        body: message,
        from: TWILIO_PHONE_NUMBER,
        to: phoneNumber
      };
      console.log(`[SMS] Request Payload:`, JSON.stringify(requestPayload, null, 2));
      console.log(`[SMS] Sending request to Twilio API...`);
      
      const result = await twilioClient.messages.create(requestPayload);
      
      const duration = Date.now() - startTime;
      console.log(`[SMS] ✅ SMS sent successfully!`);
      console.log(`[SMS] Response Time: ${duration}ms`);
      console.log(`[SMS] Message SID: ${result.sid}`);
      console.log(`[SMS] Status: ${result.status}`);
      console.log(`[SMS] Account SID: ${result.accountSid}`);
      console.log(`[SMS] From: ${result.from}`);
      console.log(`[SMS] To: ${result.to}`);
      console.log(`[SMS] Date Created: ${result.dateCreated}`);
      console.log(`[SMS] Date Sent: ${result.dateSent || 'Pending'}`);
      console.log(`[SMS] Price: ${result.price || 'N/A'}`);
      console.log(`[SMS] Price Unit: ${result.priceUnit || 'N/A'}`);
      console.log(`[SMS] ============================\n`);
      
      return { success: true, sid: result.sid, status: result.status, result: result };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.log(`[SMS] ❌ SMS send failed!`);
      console.log(`[SMS] Response Time: ${duration}ms`);
      console.log(`[SMS] Error Code: ${error.code}`);
      console.log(`[SMS] Error Message: ${error.message}`);
      console.log(`[SMS] Error Status: ${error.status || 'N/A'}`);
      console.log(`[SMS] Error More Info: ${error.moreInfo || 'N/A'}`);
      console.log(`[SMS] Full Error:`, JSON.stringify(error, null, 2));
      
      if (error.code === 21608 || error.code === 21614) {
        console.error(`[SMS] ⚠️  Phone number not verified. Add ${phoneNumber} in Twilio Console → Verified Caller IDs`);
      }
      console.log(`[SMS] ============================\n`);
      
      return { success: false, error: error.message, code: error.code, status: error.status, fullError: error };
    }
  } else {
    console.log(`[SMS] ⚠️  Twilio not configured - SMS would be sent to ${phoneNumber}`);
    console.log(`[SMS] Message: ${message}`);
    console.log(`[SMS] ============================\n`);
    return { success: true, dev: true };
  }
}

// Store OTP codes temporarily (in production, use Redis or similar)
const otpStore = new Map(); // phoneNumber -> { code, expiresAt, familyId }
const childCodesStore = new Map(); // childCode -> { childId, familyId, expiresAt }

// Clean expired OTPs every 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of otpStore.entries()) {
    if (value.expiresAt < now) {
      otpStore.delete(key);
    }
  }
  for (const [key, value] of childCodesStore.entries()) {
    if (value.expiresAt < now) {
      childCodesStore.delete(key);
    }
  }
}, 5 * 60 * 1000);

async function initializeData() {
  try {
    // Create indexes
    if (db) {
      await db.collection('families').createIndex({ phoneNumber: 1 }, { unique: true });
      await db.collection('families').createIndex({ 'children._id': 1 });
      await db.collection('otpCodes').createIndex({ phoneNumber: 1 });
      await db.collection('otpCodes').createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });
    }
    console.log('[DB] Indexes created');
  } catch (error) {
    console.error('[DB] Error initializing:', error.message);
  }
}

// Helper functions
async function getFamilyByPhone(phoneNumber) {
  if (db) {
    return await db.collection('families').findOne({ phoneNumber });
  }
  return null;
}

async function getFamilyById(familyId) {
  if (db) {
    return await db.collection('families').findOne({ _id: familyId });
  }
  return null;
}

async function createFamily(phoneNumber, countryCode = '+972') {
  console.log(`\n[CREATE-FAMILY] ===== Creating New Family =====`);
  console.log(`[CREATE-FAMILY] Phone Number: ${phoneNumber}`);
  console.log(`[CREATE-FAMILY] Country Code: ${countryCode}`);
  const fullPhoneNumber = `${countryCode}${phoneNumber}`;
  console.log(`[CREATE-FAMILY] Full Phone Number: ${fullPhoneNumber}`);
  
  const familyId = `family_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  console.log(`[CREATE-FAMILY] Family ID: ${familyId}`);
  
  const family = {
    _id: familyId,
    phoneNumber: fullPhoneNumber,
    countryCode,
    createdAt: new Date().toISOString(),
    children: [],
    categories: [
      { _id: 'cat_1', name: 'משחקים', activeFor: [] },
      { _id: 'cat_2', name: 'ממתקים', activeFor: [] },
      { _id: 'cat_3', name: 'בגדים', activeFor: [] },
      { _id: 'cat_4', name: 'בילויים', activeFor: [] },
      { _id: 'cat_5', name: 'אחר', activeFor: [] }
    ]
  };
  
  if (db) {
    await db.collection('families').insertOne(family);
    console.log(`[CREATE-FAMILY] ✅ Family saved to database`);
  } else {
    console.log(`[CREATE-FAMILY] ⚠️  Using in-memory storage (no DB)`);
  }
  
  console.log(`[CREATE-FAMILY] ============================\n`);
  return family;
}

async function addChildToFamily(familyId, childName) {
  console.log(`\n[ADD-CHILD] ===== Adding Child to Family =====`);
  console.log(`[ADD-CHILD] Family ID: ${familyId}`);
  console.log(`[ADD-CHILD] Child Name: ${childName}`);
  
  const childId = `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const childCode = generateChildCode();
  const childPassword = generateChildCode(); // 6-character password
  
  console.log(`[ADD-CHILD] Child ID: ${childId}`);
  console.log(`[ADD-CHILD] Join Code: ${childCode}`);
  console.log(`[ADD-CHILD] Password: ${childPassword}`);
  
  const child = {
    _id: childId,
    name: childName,
    balance: 0,
    cashBoxBalance: 0,
    profileImage: null,
    weeklyAllowance: 0,
    allowanceType: 'weekly',
    allowanceDay: 1,
    allowanceTime: '08:00',
    transactions: [],
    joinCode: childCode,
    password: childPassword,
    createdAt: new Date().toISOString()
  };
  
  // Store child code for 30 days
  childCodesStore.set(childCode, {
    childId,
    familyId,
    expiresAt: Date.now() + (30 * 24 * 60 * 60 * 1000)
  });
  console.log(`[ADD-CHILD] Child code stored (expires in 30 days)`);
  
  if (db) {
    await db.collection('families').updateOne(
      { _id: familyId },
      { 
        $push: { children: child },
        $push: { 'categories.$[].activeFor': childId }
      }
    );
    console.log(`[ADD-CHILD] ✅ Child saved to database`);
    
    // Update categories to include new child
    const family = await getFamilyById(familyId);
    if (family) {
      for (const category of family.categories) {
        if (!category.activeFor.includes(childId)) {
          category.activeFor.push(childId);
        }
      }
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { categories: family.categories } }
      );
      console.log(`[ADD-CHILD] Categories updated for child`);
    }
  } else {
    console.log(`[ADD-CHILD] ⚠️  Using in-memory storage (no DB)`);
  }
  
  console.log(`[ADD-CHILD] ============================\n`);
  return { child, childCode, childPassword };
}

async function joinChildByCode(familyId, childCode) {
  const codeData = childCodesStore.get(childCode);
  if (!codeData || codeData.expiresAt < Date.now()) {
    return null;
  }
  
  if (codeData.familyId !== familyId) {
    return null; // Code belongs to different family
  }
  
  if (db) {
    const family = await getFamilyById(familyId);
    if (family) {
      const child = family.children.find(c => c._id === codeData.childId);
      if (child) {
        // Update categories
        for (const category of family.categories) {
          if (!category.activeFor.includes(child._id)) {
            category.activeFor.push(child._id);
          }
        }
        await db.collection('families').updateOne(
          { _id: familyId },
          { $set: { categories: family.categories } }
        );
        return child;
      }
    }
  }
  
  return null;
}

async function getChildPassword(familyId, childId) {
  if (db) {
    const family = await getFamilyById(familyId);
    if (family) {
      const child = family.children.find(c => c._id === childId);
      return child ? child.password : null;
    }
  }
  return null;
}

// Process allowances for a family
async function processAllowancesForFamily(familyId) {
  try {
    const family = await getFamilyById(familyId);
    if (!family || !family.children) return;
    
    const now = new Date();
    const israelTime = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Jerusalem',
      weekday: 'long',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      day: 'numeric',
      month: 'numeric'
    }).formatToParts(now);
    
    const dayOfWeek = now.toLocaleString('en-US', { timeZone: 'Asia/Jerusalem', weekday: 'long' });
    const dayOfMonth = parseInt(israelTime.find(part => part.type === 'day').value);
    const hour = parseInt(israelTime.find(part => part.type === 'hour').value);
    const minute = parseInt(israelTime.find(part => part.type === 'minute').value);
    
    const dayNameToNumber = {
      'Sunday': 0, 'Monday': 1, 'Tuesday': 2, 'Wednesday': 3,
      'Thursday': 4, 'Friday': 5, 'Saturday': 6
    };
    const currentDayOfWeek = dayNameToNumber[dayOfWeek];
    
    for (const child of family.children) {
      if (!child.weeklyAllowance || child.weeklyAllowance <= 0) continue;
      
      const allowanceType = child.allowanceType || 'weekly';
      const allowanceDay = child.allowanceDay !== undefined ? child.allowanceDay : 1;
      const allowanceTime = child.allowanceTime || '08:00';
      const [allowanceHour, allowanceMinute] = allowanceTime.split(':').map(Number);
      
      let shouldProcess = false;
      
      if (allowanceType === 'weekly') {
        const isCorrectDay = currentDayOfWeek === allowanceDay;
        const isCorrectTime = hour === allowanceHour && minute >= allowanceMinute && minute < allowanceMinute + 1;
        shouldProcess = isCorrectDay && isCorrectTime;
        
        if (shouldProcess) {
          const startOfWeek = new Date(now);
          startOfWeek.setDate(now.getDate() - (now.getDay() + 6) % 7);
          startOfWeek.setHours(0, 0, 0, 0);
          
          const recentAllowance = (child.transactions || []).find(t => 
            t.type === 'deposit' && 
            (t.description === 'דמי כיס שבועיים' || t.description === 'דמי כיס חודשיים') &&
            new Date(t.date) >= startOfWeek
          );
          
          if (recentAllowance) continue;
        }
      } else if (allowanceType === 'monthly') {
        const isCorrectDay = dayOfMonth === allowanceDay;
        const isCorrectTime = hour === allowanceHour && minute >= allowanceMinute && minute < allowanceMinute + 1;
        shouldProcess = isCorrectDay && isCorrectTime;
        
        if (shouldProcess) {
          const startOfMonth = new Date(now);
          startOfMonth.setDate(1);
          startOfMonth.setHours(0, 0, 0, 0);
          
          const recentAllowance = (child.transactions || []).find(t => 
            t.type === 'deposit' && 
            (t.description === 'דמי כיס שבועיים' || t.description === 'דמי כיס חודשיים') &&
            new Date(t.date) >= startOfMonth
          );
          
          if (recentAllowance) continue;
        }
      }
      
      if (shouldProcess) {
        const description = allowanceType === 'weekly' ? 'דמי כיס שבועיים' : 'דמי כיס חודשיים';
        
        const transaction = {
          id: `allowance_${Date.now()}_${child._id}`,
          date: new Date().toISOString(),
          type: 'deposit',
          amount: child.weeklyAllowance,
          description: description,
          category: null,
          childId: child._id
        };
        
        const transactions = [...(child.transactions || []), transaction];
        const balance = transactions.reduce((total, t) => {
          if (t.type === 'deposit') {
            return total + t.amount;
          } else {
            return total - t.amount;
          }
        }, 0);
        
        // Update child in family
        if (db) {
          await db.collection('families').updateOne(
            { _id: familyId, 'children._id': child._id },
            { 
              $set: { 
                'children.$.balance': balance,
                'children.$.transactions': transactions
              }
            }
          );
        }
        
        console.log(`✅ Added ${allowanceType} allowance of ${child.weeklyAllowance} to ${child.name} in family ${familyId}`);
      }
    }
  } catch (error) {
    console.error('Error processing allowances:', error);
  }
}

// Check allowances every minute
setInterval(async () => {
  if (db) {
    const families = await db.collection('families').find({}).toArray();
    for (const family of families) {
      await processAllowancesForFamily(family._id);
    }
  }
}, 60 * 1000);

// ========== NEW AUTHENTICATION API ENDPOINTS ==========

// Send OTP for family registration/login
// Log test endpoint - for testing logs from frontend
app.post('/api/test-logs', (req, res) => {
  const timestamp = new Date().toISOString();
  const clientIP = req.ip || req.connection.remoteAddress;
  console.log(`[TEST-LOGS] ========================================`);
  console.log(`[TEST-LOGS] Button clicked - ${timestamp}`);
  console.log(`[TEST-LOGS] Client IP: ${clientIP}`);
  console.log(`[TEST-LOGS] User Agent: ${req.get('user-agent') || 'N/A'}`);
  console.log(`[TEST-LOGS] ========================================`);
  res.status(200).json({ success: true, message: 'Log entry created', timestamp });
});

app.post('/api/auth/send-otp', async (req, res) => {
  console.log(`[SEND-OTP] Request received: ${req.body.phoneNumber} (${req.body.countryCode || '+972'})`);
  
  try {
    const { phoneNumber, countryCode = '+972' } = req.body;
    
    if (!phoneNumber || !phoneNumber.match(/^\d+$/)) {
      return res.status(400).json({ error: 'מספר טלפון לא תקין' });
    }
    
    const fullPhoneNumber = `${countryCode}${phoneNumber}`;
    const otpCode = generateOTP();
    const expiresAt = Date.now() + (10 * 60 * 1000); // 10 minutes
    
    // Check if family exists
    const existingFamily = await getFamilyByPhone(fullPhoneNumber);
    
    // Store OTP
    otpStore.set(fullPhoneNumber, {
      code: otpCode,
      expiresAt,
      familyId: existingFamily ? existingFamily._id : null
    });
    
    // Send SMS
    const message = `קוד האימות שלך: ${otpCode}. קוד זה תקף ל-10 דקות.`;
    
    console.log(`[SEND-OTP] Sending SMS to ${fullPhoneNumber}, OTP: ${otpCode}`);
    const smsResult = await sendSMS(fullPhoneNumber, message);
    
    if (!smsResult.success) {
      console.error(`[SEND-OTP] ❌ SMS failed: ${smsResult.error} (code: ${smsResult.code})`);
      return res.status(500).json({ 
        error: 'שגיאה בשליחת SMS. אנא נסה שוב או פנה לתמיכה.',
        smsError: smsResult.error,
        smsCode: smsResult.code
      });
    }
    
    console.log(`[SEND-OTP] ✅ SMS sent successfully (SID: ${smsResult.sid})`);
    
    res.json({ 
      success: true, 
      message: 'קוד נשלח בהצלחה',
      isExistingFamily: !!existingFamily,
      smsSent: true
    });
  } catch (error) {
    console.error('Error sending OTP:', error);
    res.status(500).json({ error: 'שגיאה בשליחת קוד אימות' });
  }
});

// Verify OTP and login/register
app.post('/api/auth/verify-otp', async (req, res) => {
  try {
    const { phoneNumber, countryCode = '+972', otpCode } = req.body;
    
    if (!phoneNumber || !otpCode) {
      return res.status(400).json({ error: 'מספר טלפון וקוד אימות נדרשים' });
    }
    
    const fullPhoneNumber = `${countryCode}${phoneNumber}`;
    const storedOTP = otpStore.get(fullPhoneNumber);
    
    if (!storedOTP || storedOTP.expiresAt < Date.now()) {
      return res.status(400).json({ error: 'קוד אימות לא תקין או פג תוקף' });
    }
    
    if (storedOTP.code !== otpCode) {
      return res.status(400).json({ error: 'קוד אימות שגוי' });
    }
    
    // OTP verified - get or create family
    let family = await getFamilyByPhone(fullPhoneNumber);
    
    if (!family) {
      // Create new family
      family = await createFamily(phoneNumber, countryCode);
    }
    
    // Remove OTP
    otpStore.delete(fullPhoneNumber);
    
    res.json({
      success: true,
      familyId: family._id,
      phoneNumber: family.phoneNumber,
      isNewFamily: !storedOTP.familyId
    });
  } catch (error) {
    console.error('Error verifying OTP:', error);
    res.status(500).json({ error: 'שגיאה באימות קוד' });
  }
});

// Create child and get join code
app.post('/api/families/:familyId/children', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { name } = req.body;
    
    if (!name) {
      return res.status(400).json({ error: 'שם הילד נדרש' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const { child, childCode, childPassword } = await addChildToFamily(familyId, name);
    
    res.json({
      success: true,
      child: {
        _id: child._id,
        name: child.name,
        balance: child.balance,
        cashBoxBalance: child.cashBoxBalance,
        profileImage: child.profileImage,
        weeklyAllowance: child.weeklyAllowance,
        allowanceType: child.allowanceType,
        allowanceDay: child.allowanceDay,
        allowanceTime: child.allowanceTime,
        transactions: child.transactions
      },
      joinCode: childCode,
      password: childPassword
    });
  } catch (error) {
    console.error('Error creating child:', error);
    res.status(500).json({ error: 'שגיאה ביצירת ילד' });
  }
});

// Join child by code
app.post('/api/families/:familyId/children/join', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { joinCode } = req.body;
    
    if (!joinCode) {
      return res.status(400).json({ error: 'קוד הצטרפות נדרש' });
    }
    
    const child = await joinChildByCode(familyId, joinCode);
    
    if (!child) {
      return res.status(400).json({ error: 'קוד הצטרפות לא תקין או פג תוקף' });
    }
    
    res.json({
      success: true,
      child: {
        _id: child._id,
        name: child.name,
        balance: child.balance,
        cashBoxBalance: child.cashBoxBalance,
        profileImage: child.profileImage,
        weeklyAllowance: child.weeklyAllowance,
        allowanceType: child.allowanceType,
        allowanceDay: child.allowanceDay,
        allowanceTime: child.allowanceTime,
        transactions: child.transactions
      }
    });
  } catch (error) {
    console.error('Error joining child:', error);
    res.status(500).json({ error: 'שגיאה בהצטרפות ילד' });
  }
});

// Get child password (for recovery)
app.get('/api/families/:familyId/children/:childId/password', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    
    const password = await getChildPassword(familyId, childId);
    
    if (!password) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    res.json({
      success: true,
      password
    });
  } catch (error) {
    console.error('Error getting child password:', error);
    res.status(500).json({ error: 'שגיאה בקבלת סיסמה' });
  }
});

// ========== UPDATED API ENDPOINTS (with family support) ==========

// Get all children for a family
app.get('/api/families/:familyId/children', async (req, res) => {
  try {
    const { familyId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const children = (family.children || []).map(child => ({
      _id: child._id,
      name: child.name,
      balance: child.balance || 0,
      cashBoxBalance: child.cashBoxBalance || 0,
      profileImage: child.profileImage || null,
      weeklyAllowance: child.weeklyAllowance || 0,
      allowanceType: child.allowanceType || 'weekly',
      allowanceDay: child.allowanceDay !== undefined ? child.allowanceDay : 1,
      allowanceTime: child.allowanceTime || '08:00',
      transactions: child.transactions || []
    }));
    
    res.json({ children: children.reduce((acc, child) => {
      acc[child._id] = child;
      return acc;
    }, {}) });
  } catch (error) {
    console.error('Error fetching children:', error);
    res.status(500).json({ error: 'Failed to fetch children' });
  }
});

// Get single child
app.get('/api/families/:familyId/children/:childId', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    res.json({
      name: child.name,
      balance: child.balance || 0,
      cashBoxBalance: child.cashBoxBalance || 0,
      profileImage: child.profileImage || null,
      weeklyAllowance: child.weeklyAllowance || 0,
      allowanceType: child.allowanceType || 'weekly',
      allowanceDay: child.allowanceDay !== undefined ? child.allowanceDay : 1,
      allowanceTime: child.allowanceTime || '08:00',
      transactions: child.transactions || []
    });
  } catch (error) {
    console.error('Error fetching child:', error);
    res.status(500).json({ error: 'Failed to fetch child' });
  }
});

// Get transactions for a child
app.get('/api/families/:familyId/children/:childId/transactions', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    const limit = req.query.limit ? parseInt(req.query.limit) : null;
    let transactions = [...(child.transactions || [])].sort((a, b) => 
      new Date(b.date) - new Date(a.date)
    );
    
    if (limit) {
      transactions = transactions.slice(0, limit);
    }
    
    res.json({ transactions });
  } catch (error) {
    console.error('Error fetching transactions:', error);
    res.status(500).json({ error: 'Failed to fetch transactions' });
  }
});

// Add transaction
app.post('/api/families/:familyId/transactions', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { childId, type, amount, description, category } = req.body;
    
    if (!childId || !type || !amount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    // Validate category
    if (type === 'expense' && category) {
      const validCategories = (family.categories || [])
        .filter(cat => (cat.activeFor || []).includes(childId))
        .map(cat => cat.name);
      
      if (!validCategories.includes(category)) {
        return res.status(400).json({ error: 'Invalid category' });
      }
    }
    
    const transactionId = crypto.randomUUID ? crypto.randomUUID() : 
      'txn_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    
    const transaction = {
      id: transactionId,
      date: new Date().toISOString(),
      type: type,
      amount: parseFloat(amount),
      description: description || '',
      category: type === 'expense' ? (category || 'אחר') : null,
      childId: childId
    };
    
    const transactions = [...(child.transactions || []), transaction];
    const balance = transactions.reduce((total, t) => {
      if (t.type === 'deposit') {
        return total + t.amount;
      } else {
        return total - t.amount;
      }
    }, 0);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $set: { 
            'children.$.balance': balance,
            'children.$.transactions': transactions
          }
        }
      );
    }
    
    res.json({ transaction, balance, updated: true });
  } catch (error) {
    console.error('Error adding transaction:', error);
    res.status(500).json({ error: 'Failed to add transaction' });
  }
});

// Get expenses by category
app.get('/api/families/:familyId/children/:childId/expenses-by-category', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const days = parseInt(req.query.days) || 30;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    const cutoffDate = new Date();
    cutoffDate.setHours(0, 0, 0, 0);
    cutoffDate.setDate(cutoffDate.getDate() - days + 1);
    
    const expenses = (child.transactions || [])
      .filter(t => {
        if (t.type !== 'expense') return false;
        const transactionDate = new Date(t.date);
        transactionDate.setHours(0, 0, 0, 0);
        return transactionDate >= cutoffDate;
      });
    
    const activeCategories = (family.categories || [])
      .filter(cat => (cat.activeFor || []).includes(childId))
      .map(cat => cat.name);
    
    const categoryTotals = {};
    activeCategories.forEach(cat => {
      categoryTotals[cat] = 0;
    });
    if (!categoryTotals.hasOwnProperty('אחר')) {
      categoryTotals['אחר'] = 0;
    }
    
    expenses.forEach(expense => {
      const category = expense.category || 'אחר';
      if (categoryTotals.hasOwnProperty(category)) {
        categoryTotals[category] += expense.amount;
      } else {
        categoryTotals['אחר'] += expense.amount;
      }
    });
    
    const result = Object.entries(categoryTotals)
      .filter(([_, amount]) => amount > 0)
      .map(([category, amount]) => ({ category, amount }));
    
    res.json({ expensesByCategory: result, totalDays: days });
  } catch (error) {
    console.error('Error fetching expenses by category:', error);
    res.status(500).json({ error: 'Failed to fetch expenses by category' });
  }
});

// Update cash box balance
app.put('/api/families/:familyId/children/:childId/cashbox', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const { cashBoxBalance } = req.body;
    
    if (cashBoxBalance === undefined || cashBoxBalance === null) {
      return res.status(400).json({ error: 'cashBoxBalance is required' });
    }
    
    const amount = parseFloat(cashBoxBalance);
    if (isNaN(amount) || amount < 0) {
      return res.status(400).json({ error: 'cashBoxBalance must be a valid non-negative number' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { $set: { 'children.$.cashBoxBalance': amount } }
      );
    }
    
    res.json({
      success: true,
      cashBoxBalance: amount,
      message: 'Cash box balance updated successfully'
    });
  } catch (error) {
    console.error('Error updating cash box balance:', error);
    res.status(500).json({ error: 'Failed to update cash box balance' });
  }
});

// Categories API
app.get('/api/families/:familyId/categories', async (req, res) => {
  try {
    const { familyId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    res.json({ categories: family.categories || [] });
  } catch (error) {
    console.error('Error fetching categories:', error);
    res.status(500).json({ error: 'Failed to fetch categories' });
  }
});

app.post('/api/families/:familyId/categories', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { name, activeFor } = req.body;
    
    if (!name) {
      return res.status(400).json({ error: 'Category name is required' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const category = {
      _id: `cat_${Date.now()}`,
      name: name.trim(),
      activeFor: activeFor || []
    };
    
    family.categories.push(category);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { categories: family.categories } }
      );
    }
    
    res.json({ category });
  } catch (error) {
    console.error('Error adding category:', error);
    res.status(500).json({ error: 'Failed to add category' });
  }
});

app.put('/api/families/:familyId/categories/:categoryId', async (req, res) => {
  try {
    const { familyId, categoryId } = req.params;
    const { name, activeFor } = req.body;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const category = family.categories.find(c => c._id === categoryId);
    if (!category) {
      return res.status(404).json({ error: 'Category not found' });
    }
    
    if (name !== undefined) category.name = name.trim();
    if (activeFor !== undefined) category.activeFor = activeFor;
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { categories: family.categories } }
      );
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error updating category:', error);
    res.status(500).json({ error: 'Failed to update category' });
  }
});

app.delete('/api/families/:familyId/categories/:categoryId', async (req, res) => {
  try {
    const { familyId, categoryId } = req.params;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    family.categories = family.categories.filter(c => c._id !== categoryId);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { categories: family.categories } }
      );
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting category:', error);
    res.status(500).json({ error: 'Failed to delete category' });
  }
});

// Update profile image
app.put('/api/families/:familyId/children/:childId/profile-image', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const { profileImage } = req.body;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    if (profileImage && !profileImage.startsWith('data:image/')) {
      return res.status(400).json({ error: 'Invalid image format' });
    }
    
    if (profileImage && profileImage.length > 5 * 1024 * 1024) {
      return res.status(400).json({ error: 'Image too large' });
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { $set: { 'children.$.profileImage': profileImage || null } }
      );
    }
    
    res.json({ success: true, profileImage: profileImage || null });
  } catch (error) {
    console.error('Error updating profile image:', error);
    res.status(500).json({ error: 'Failed to update profile image' });
  }
});

// Update weekly allowance
app.put('/api/families/:familyId/children/:childId/weekly-allowance', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const { weeklyAllowance, allowanceType, allowanceDay, allowanceTime } = req.body;
    
    const amount = parseFloat(weeklyAllowance);
    if (isNaN(amount) || amount < 0) {
      return res.status(400).json({ error: 'Weekly allowance must be a valid non-negative number' });
    }
    
    const type = allowanceType || 'weekly';
    if (type !== 'weekly' && type !== 'monthly') {
      return res.status(400).json({ error: 'Allowance type must be "weekly" or "monthly"' });
    }
    
    let day = allowanceDay !== undefined ? parseInt(allowanceDay) : 1;
    if (type === 'weekly') {
      if (day < 0 || day > 6) {
        return res.status(400).json({ error: 'Weekly allowance day must be 0-6' });
      }
    } else {
      if (day < 1 || day > 31) {
        return res.status(400).json({ error: 'Monthly allowance day must be 1-31' });
      }
    }
    
    const time = allowanceTime || '08:00';
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timeRegex.test(time)) {
      return res.status(400).json({ error: 'Allowance time must be in HH:mm format' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $set: { 
            'children.$.weeklyAllowance': amount,
            'children.$.allowanceType': type,
            'children.$.allowanceDay': day,
            'children.$.allowanceTime': time
          }
        }
      );
    }
    
    res.json({ success: true, weeklyAllowance: amount, allowanceType: type, allowanceDay: day, allowanceTime: time });
  } catch (error) {
    console.error('Error updating weekly allowance:', error);
    res.status(500).json({ error: 'Failed to update weekly allowance' });
  }
});

// Pay allowance manually
app.post('/api/families/:familyId/children/:childId/pay-allowance', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    if (!child.weeklyAllowance || child.weeklyAllowance <= 0) {
      return res.status(400).json({ error: 'Allowance is not set for this child' });
    }
    
    const allowanceType = child.allowanceType || 'weekly';
    const description = allowanceType === 'weekly' ? 'דמי כיס שבועיים' : 'דמי כיס חודשיים';
    
    const now = new Date();
    let cutoffDate;
    if (allowanceType === 'weekly') {
      cutoffDate = new Date(now);
      cutoffDate.setDate(now.getDate() - 7);
    } else {
      cutoffDate = new Date(now);
      cutoffDate.setDate(1);
      cutoffDate.setHours(0, 0, 0, 0);
    }
    
    const recentAllowance = (child.transactions || []).find(t => 
      t.type === 'deposit' && 
      (t.description === 'דמי כיס שבועיים' || t.description === 'דמי כיס חודשיים') &&
      new Date(t.date) > cutoffDate
    );
    
    if (recentAllowance) {
      return res.status(400).json({ error: 'Allowance already added this week' });
    }
    
    const transaction = {
      id: `allowance_${Date.now()}_${child._id}`,
      date: new Date().toISOString(),
      type: 'deposit',
      amount: child.weeklyAllowance,
      description: description,
      category: null,
      childId: child._id
    };
    
    const transactions = [...(child.transactions || []), transaction];
    const balance = transactions.reduce((total, t) => {
      if (t.type === 'deposit') {
        return total + t.amount;
      } else {
        return total - t.amount;
      }
    }, 0);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $set: { 
            'children.$.balance': balance,
            'children.$.transactions': transactions
          }
        }
      );
    }
    
    res.json({ success: true, transaction, balance });
  } catch (error) {
    console.error('Error paying allowance:', error);
    res.status(500).json({ error: 'Failed to pay allowance' });
  }
});

// REMOVED: Duplicate /api/health endpoint - already defined above
// This was causing confusion - keeping only the one defined before middleware

// /health is already defined at the top (before middleware) - no duplicate needed

// /api/health is already defined above, no need for duplicate

// Root endpoint is already defined at the top - no duplicate needed

// Start server
let server;

// Start server immediately, don't wait for DB
// Railway needs the server to respond to health checks immediately
server = app.listen(PORT, '0.0.0.0', () => {
  serverReady = true;
  console.log(`[SERVER] Version ${VERSION} - Started on port ${PORT}`);
  console.log(`[SERVER] Health check: http://0.0.0.0:${PORT}/health`);
  console.log(`[SERVER] Server is ready and listening`);
  console.log(`[SERVER] ✅ Server is now ready to accept health checks`);
  console.log(`[SERVER] ⚠️  Waiting for Railway health check calls...`);
  console.log(`[SERVER] ⚠️  If no health check calls appear, service may be configured as 'Job' instead of 'Web Service'`);
  
  // Start heartbeat to keep container alive and log activity
  // Railway sometimes needs activity to know the service is alive
  let heartbeatCount = 0;
  setInterval(() => {
    if (serverReady) {
      heartbeatCount++;
      const uptime = process.uptime();
      const timeSinceLastHealthCheck = Date.now() - lastHealthCheckTime;
      console.log(`[HEARTBEAT] Server is alive - uptime: ${Math.floor(uptime)}s, heartbeat: ${heartbeatCount}, health checks received: ${healthCheckCount}, last check: ${Math.floor(timeSinceLastHealthCheck / 1000)}s ago`);
      
      // If no health checks for 5 minutes, log warning
      if (timeSinceLastHealthCheck > 300000 && healthCheckCount > 0) {
        console.log(`[HEARTBEAT] ⚠️  WARNING: No health checks for ${Math.floor(timeSinceLastHealthCheck / 1000)}s - Railway may be configured as Job`);
      }
    }
  }, 30000); // Every 30 seconds
});

server.on('error', (error) => {
  console.error('[SERVER] Error:', error);
});

server.on('listening', () => {
  console.log(`[SERVER] Version ${VERSION} - Listening on http://0.0.0.0:${PORT}`);
  console.log(`[SERVER] Health check endpoint is ready at /health`);
  console.log(`[SERVER] ✅ Health check is now available`);
});

// Handle shutdown gracefully
let isShuttingDown = false;

// Track SIGTERM calls but don't shut down - continue running
let sigtermCount = 0;
process.on('SIGTERM', () => {
  sigtermCount++;
  const uptime = process.uptime();
  const timeSinceLastHealthCheck = Date.now() - lastHealthCheckTime;
  
  console.log(`\n[SERVER] ⚠️  ========================================`);
  console.log(`[SERVER] ⚠️  SIGTERM received (call #${sigtermCount})`);
  console.log(`[SERVER] ⚠️  Server has been running for ${Math.floor(uptime)} seconds`);
  console.log(`[SERVER] ⚠️  Server ready status: ${serverReady ? 'YES' : 'NO'}`);
  console.log(`[SERVER] ⚠️  Port (process.env.PORT): ${process.env.PORT || 'NOT SET'}`);
  console.log(`[SERVER] ⚠️  Port (actual): ${PORT}`);
  console.log(`[SERVER] ⚠️  Server listening: ${server && server.listening ? 'YES' : 'NO'}`);
  console.log(`[SERVER] ⚠️  Health check URL: http://0.0.0.0:${PORT}/health`);
  console.log(`[SERVER] ⚠️  Total health check calls received: ${healthCheckCount}`);
  console.log(`[SERVER] ⚠️  Last health check: ${Math.floor(timeSinceLastHealthCheck / 1000)}s ago`);
  
  if (healthCheckCount === 0) {
    console.log(`[SERVER] ❌ CRITICAL: No health check calls were received!`);
    console.log(`[SERVER] ❌ This means Railway is NOT calling /health endpoint`);
    console.log(`[SERVER] ❌ Service is DEFINITELY configured as 'Job' instead of 'Web Service'`);
    console.log(`[SERVER] ❌ SOLUTION: Railway Dashboard → Settings → Service Type → Change to 'Web Service'`);
  } else if (timeSinceLastHealthCheck > 300000) {
    console.log(`[SERVER] ❌ CRITICAL: No health checks for ${Math.floor(timeSinceLastHealthCheck / 1000)}s!`);
    console.log(`[SERVER] ❌ Railway stopped calling /health after ${healthCheckCount} calls`);
    console.log(`[SERVER] ❌ Service is likely configured as 'Job' - it runs once and stops`);
    console.log(`[SERVER] ❌ SOLUTION: Railway Dashboard → Settings → Service Type → Change to 'Web Service'`);
  } else {
    console.log(`[SERVER] ⚠️  Health checks were received (${healthCheckCount} total) but Railway still sent SIGTERM`);
    console.log(`[SERVER] ⚠️  This may indicate health check response format issue`);
  }
  
  console.log(`[SERVER] ⚠️  ========================================`);
  console.log(`[SERVER] ⚠️  IGNORING SIGTERM - Server will continue running`);
  console.log(`[SERVER] ⚠️  Server is still active and accepting requests`);
  console.log(`[SERVER] ⚠️  Note: Railway may force kill the container, but we'll try to keep running`);
  console.log(`[SERVER] ⚠️  ========================================\n`);
  
  // DO NOT shut down - continue running
  // Railway may force kill the container, but we'll try to keep running
});
  
process.on('SIGINT', () => {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log('[SERVER] SIGINT received, shutting down...');
  if (server) {
    server.close(() => {
      process.exit(0);
    });
  } else {
    process.exit(0);
  }
});

// Handle uncaught errors - don't crash on errors
process.on('uncaughtException', (error) => {
  console.error('[ERROR] Uncaught Exception:', error.message);
  // Don't exit - let Railway handle it
});

process.on('unhandledRejection', (reason) => {
  console.error('[ERROR] Unhandled Rejection:', reason);
  // Don't exit - let Railway handle it
});

// Connect to DB in background (don't block server startup)
// This happens after server is already listening
setTimeout(() => {
  connectDB();
}, 100);

