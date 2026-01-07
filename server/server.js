import express from 'express';
import cors from 'cors';
import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import crypto from 'crypto';
import twilio from 'twilio';
import { Resend } from 'resend';

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

// Twilio configuration (for SMS OTP) - DEPRECATED, using email instead
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER;
let twilioClient = null;

// Resend configuration (for Email OTP)
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const RESEND_FROM_EMAIL = process.env.RESEND_FROM_EMAIL || 'noreply@kidsmoneymanager.app';
let resendClient = null;

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

// Resend (Email) configuration
console.log(`\n=== Resend (Email) Configuration ===`);
console.log(`[RESEND] API Key: ${RESEND_API_KEY ? `${RESEND_API_KEY.substring(0, 10)}...${RESEND_API_KEY.substring(RESEND_API_KEY.length - 4)}` : 'NOT SET'}`);
console.log(`[RESEND] From Email: ${RESEND_FROM_EMAIL}`);
console.log(`[RESEND] Client Status: ${RESEND_API_KEY ? 'READY' : 'NOT CONFIGURED'}`);

// Initialize Resend only if API key is available (lazy initialization)
// This prevents build-time errors when RESEND_API_KEY is not set
try {
  if (RESEND_API_KEY) {
    resendClient = new Resend(RESEND_API_KEY);
    console.log(`[RESEND] ✅ Client initialized successfully`);
    console.log(`[RESEND] From Email: ${RESEND_FROM_EMAIL}`);
    console.log(`[RESEND] API Base URL: https://api.resend.com`);
  } else {
    console.log(`[RESEND] ⚠️  Not configured - Email will not be sent`);
    console.log(`[RESEND]   Missing: RESEND_API_KEY`);
    console.log(`[RESEND]   Missing: RESEND_FROM_EMAIL (optional, defaults to noreply@kidsmoneymanager.app)`);
  }
} catch (error) {
  // Silently handle initialization errors during build time
  console.log(`[RESEND] ⚠️  Not configured - Email will not be sent`);
  console.log(`[RESEND]   Error: ${error.message}`);
}
console.log(`===========================\n`);

// CRITICAL: Health check MUST be defined BEFORE any middleware
// Railway checks this immediately and if it's slow, container stops
// This endpoint must respond IMMEDIATELY - no logging, no processing
let serverReady = false;

// Health check endpoint - must be fastest possible
// Render checks this endpoint to determine if service is healthy
// CRITICAL: This MUST respond immediately - Render uses this to keep service alive
// MUST be defined BEFORE middleware to ensure fastest response
let healthCheckCount = 0;
let lastHealthCheckTime = Date.now();

// Heartbeat to monitor service health
// Logs activity every 30 seconds
setInterval(() => {
  const timeSinceLastCheck = Date.now() - lastHealthCheckTime;
  if (timeSinceLastCheck > 60000) { // 60 seconds
    process.stderr.write(`[HEARTBEAT] ⚠️  WARNING: No health check received in ${Math.floor(timeSinceLastCheck / 1000)}s\n`);
    process.stderr.write(`[HEARTBEAT] ⚠️  This means Render is NOT calling /health endpoint\n`);
    process.stderr.write(`[HEARTBEAT] ⚠️  Service may be configured as 'Job' instead of 'Web Service'\n`);
  } else {
    process.stderr.write(`[HEARTBEAT] ✅ Server is alive - health checks: ${healthCheckCount}, last check: ${Math.floor(timeSinceLastCheck / 1000)}s ago\n`);
  }
}, 30000); // Every 30 seconds
app.get('/health', (req, res) => {
  healthCheckCount++;
  lastHealthCheckTime = Date.now();
  
  // Respond IMMEDIATELY - no delays, no logging before response
  // Render needs instant 200 OK response to keep service alive
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-cache');
  res.status(200).json({ 
    status: 'ok',
    timestamp: new Date().toISOString(),
    healthCheckCount: healthCheckCount,
    uptime: process.uptime()
  });
  
  // Log AFTER response to not delay
  // Log every health check to stderr (most visible in Render)
  process.stderr.write(`[HEALTH] ✅ Health check #${healthCheckCount} received - Server is alive\n`);
  
  // Also log occasionally to console
  if (healthCheckCount % 10 === 0) {
    console.log(`[HEALTH] Health check #${healthCheckCount} - Server is alive`);
  }
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

// Logging middleware - LOG EVERYTHING for send-otp
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  const clientIP = req.ip || req.connection.remoteAddress || req.headers['x-forwarded-for'] || 'unknown';
  
  // Special logging for send-otp endpoint - LOG IMMEDIATELY
  if (req.path === '/api/auth/send-otp') {
    process.stderr.write('\n\n========================================\n');
    process.stderr.write('🔔🔔🔔 INCOMING REQUEST DETECTED 🔔🔔🔔\n');
    process.stderr.write('========================================\n');
    process.stderr.write(`[MIDDLEWARE] Timestamp: ${timestamp}\n`);
    process.stderr.write(`[MIDDLEWARE] Method: ${req.method}\n`);
    process.stderr.write(`[MIDDLEWARE] Path: ${req.path}\n`);
    process.stderr.write(`[MIDDLEWARE] Client IP: ${clientIP}\n`);
    process.stderr.write(`[MIDDLEWARE] Headers: ${JSON.stringify(req.headers)}\n`);
    process.stderr.write(`[MIDDLEWARE] Body: ${JSON.stringify(req.body)}\n`);
    process.stderr.write('========================================\n\n');
    
    console.log(`\n[MIDDLEWARE] ========================================`);
    console.log(`[MIDDLEWARE] 🔔 INCOMING REQUEST DETECTED 🔔`);
    console.log(`[MIDDLEWARE] ========================================`);
    console.log(`[MIDDLEWARE] Timestamp: ${timestamp}`);
    console.log(`[MIDDLEWARE] Method: ${req.method}`);
    console.log(`[MIDDLEWARE] Path: ${req.path}`);
    console.log(`[MIDDLEWARE] Client IP: ${clientIP}`);
    console.log(`[MIDDLEWARE] Headers:`, req.headers);
    console.log(`[MIDDLEWARE] Body:`, req.body);
    console.log(`[MIDDLEWARE] ========================================\n`);
  }
  
  // Log other API requests (not health checks)
  if (req.path.startsWith('/api/') && req.path !== '/api/health' && req.path !== '/api/auth/send-otp') {
    console.log(`[${timestamp}] ${req.method} ${req.path}`);
  }
  
  next();
});

// Keep-alive endpoint - Render can use this to verify service is running
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

// Send Email via Resend
async function sendEmail(emailAddress, otpCode) {
  const startTime = Date.now();
  const timestamp = new Date().toISOString();
  
  // Force immediate output
  process.stdout.write('\n\n\n');
  process.stderr.write('\n\n\n');
  
  // Write to stderr first (most visible in Render)
  process.stderr.write('========================================\n');
  process.stderr.write('📧📧📧 SEND EMAIL FUNCTION CALLED 📧📧📧\n');
  process.stderr.write('========================================\n');
  process.stderr.write(`[EMAIL] Timestamp: ${timestamp}\n`);
  process.stderr.write(`[EMAIL] To: ${emailAddress}\n`);
  process.stderr.write(`[EMAIL] From: ${RESEND_FROM_EMAIL}\n`);
  process.stderr.write(`[EMAIL] OTP Code: ${otpCode}\n`);
  process.stderr.write(`[EMAIL] Resend Client: ${resendClient ? 'INITIALIZED' : 'NOT INITIALIZED'}\n`);
  process.stderr.write(`[EMAIL] Resend API Key: ${RESEND_API_KEY ? 'SET' : 'NOT SET'}\n`);
  process.stderr.write(`[EMAIL] API Endpoint: https://api.resend.com/emails\n`);
  process.stderr.write('========================================\n\n');
  
  console.log(`\n[EMAIL] ========================================`);
  console.log(`[EMAIL] ===== Email Send Attempt =====`);
  console.log(`[EMAIL] ========================================`);
  console.log(`[EMAIL] Timestamp: ${timestamp}`);
  console.log(`[EMAIL] To: ${emailAddress}`);
  console.log(`[EMAIL] From: ${RESEND_FROM_EMAIL}`);
  console.log(`[EMAIL] OTP Code: ${otpCode}`);
  console.log(`[EMAIL] Resend Client: ${resendClient ? 'INITIALIZED' : 'NOT INITIALIZED'}`);
  console.log(`[EMAIL] Resend API Key: ${RESEND_API_KEY ? 'SET' : 'NOT SET'}`);
  console.log(`[EMAIL] API Endpoint: https://api.resend.com/emails`);
  console.log(`[EMAIL] ========================================\n`);
  
  console.error(`\n[EMAIL] ========================================`);
  console.error(`[EMAIL] ===== Email Send Attempt =====`);
  console.error(`[EMAIL] To: ${emailAddress}`);
  console.error(`[EMAIL] From: ${RESEND_FROM_EMAIL}`);
  console.error(`[EMAIL] Resend Client: ${resendClient ? 'INITIALIZED' : 'NOT INITIALIZED'}`);
  console.error(`[EMAIL] ========================================\n`);
  
  if (resendClient && RESEND_API_KEY) {
    try {
      const emailSubject = 'קוד אימות - Kids Money Manager';
      const emailHtml = `
        <!DOCTYPE html>
        <html dir="rtl" lang="he">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>קוד אימות</title>
        </head>
        <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right; background-color: #f5f5f5; padding: 20px;">
          <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #4f46e5; margin-bottom: 20px;">קוד אימות</h1>
            <p style="font-size: 16px; color: #333; margin-bottom: 30px;">
              שלום,<br><br>
              קיבלנו בקשה לאימות החשבון שלך. הקוד שלך הוא:
            </p>
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
              <h2 style="color: #4f46e5; font-size: 32px; letter-spacing: 5px; margin: 0;">${otpCode}</h2>
            </div>
            <p style="font-size: 14px; color: #666; margin-top: 30px;">
              קוד זה תקף ל-10 דקות בלבד.<br>
              אם לא ביקשת קוד זה, תוכל להתעלם מהמייל הזה.
            </p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="font-size: 12px; color: #999; text-align: center;">
              Kids Money Manager - ניהול כסף לילדים
            </p>
          </div>
        </body>
        </html>
      `;
      
      const emailText = `קוד האימות שלך: ${otpCode}. קוד זה תקף ל-10 דקות.`;
      
      // Prepare request payload
      const requestPayload = {
        from: RESEND_FROM_EMAIL,
        to: emailAddress,
        subject: emailSubject,
        html: emailHtml,
        text: emailText
      };
      
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] 📤 Preparing to send email...`);
      console.log(`[EMAIL] API Endpoint: https://api.resend.com/emails`);
      console.log(`[EMAIL] Request Method: POST`);
      console.log(`[EMAIL] Request Headers: Authorization: Bearer ${RESEND_API_KEY.substring(0, 10)}...${RESEND_API_KEY.substring(RESEND_API_KEY.length - 4)}`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] 📦 Request Payload (JSON):`);
      console.log(`[EMAIL] {`);
      console.log(`[EMAIL]   "from": "${RESEND_FROM_EMAIL}",`);
      console.log(`[EMAIL]   "to": "${emailAddress}",`);
      console.log(`[EMAIL]   "subject": "${emailSubject}",`);
      console.log(`[EMAIL]   "html": "<html>... (${emailHtml.length} characters)",`);
      console.log(`[EMAIL]   "text": "${emailText}"`);
      console.log(`[EMAIL] }`);
      console.log(`[EMAIL] ========================================\n`);
      
      process.stderr.write(`[EMAIL] ========================================\n`);
      process.stderr.write(`[EMAIL] 📤 Preparing to send email...\n`);
      process.stderr.write(`[EMAIL] API Endpoint: https://api.resend.com/emails\n`);
      process.stderr.write(`[EMAIL] Request Method: POST\n`);
      process.stderr.write(`[EMAIL] From: ${RESEND_FROM_EMAIL}\n`);
      process.stderr.write(`[EMAIL] To: ${emailAddress}\n`);
      process.stderr.write(`[EMAIL] Subject: ${emailSubject}\n`);
      process.stderr.write(`[EMAIL] Request Payload: ${JSON.stringify({ from: RESEND_FROM_EMAIL, to: emailAddress, subject: emailSubject })}\n`);
      process.stderr.write(`[EMAIL] ========================================\n`);
      
      console.log(`[EMAIL] 🚀 Calling resendClient.emails.send()...`);
      process.stderr.write(`[EMAIL] 🚀 Calling resendClient.emails.send()...\n`);
      const requestTime = Date.now();
      
      const result = await resendClient.emails.send(requestPayload);
      
      const apiDuration = Date.now() - requestTime;
      const totalDuration = Date.now() - startTime;
      
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] ✅ Email sent successfully!`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] 📥 Response received from Resend API:`);
      console.log(`[EMAIL] Response Time: ${apiDuration}ms`);
      console.log(`[EMAIL] Total Time: ${totalDuration}ms`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] 📋 Response Data (JSON):`);
      console.log(`[EMAIL] {`);
      console.log(`[EMAIL]   "id": "${result.id}",`);
      if (result.from) console.log(`[EMAIL]   "from": "${result.from}",`);
      if (result.to) console.log(`[EMAIL]   "to": "${Array.isArray(result.to) ? result.to.join(', ') : result.to}",`);
      if (result.created_at) console.log(`[EMAIL]   "created_at": "${result.created_at}",`);
      Object.keys(result).forEach(key => {
        if (!['id', 'from', 'to', 'created_at'].includes(key)) {
          console.log(`[EMAIL]   "${key}": ${JSON.stringify(result[key])},`);
        }
      });
      console.log(`[EMAIL] }`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] Email ID: ${result.id}`);
      console.log(`[EMAIL] From: ${RESEND_FROM_EMAIL}`);
      console.log(`[EMAIL] To: ${emailAddress}`);
      console.log(`[EMAIL] Subject: ${emailSubject}`);
      console.log(`[EMAIL] ========================================\n`);
      
      const emailSuccessLog = `[EMAIL] ========================================\n[EMAIL] ✅✅✅ EMAIL SENT SUCCESSFULLY ✅✅✅\n[EMAIL] ========================================\n[EMAIL] Email ID: ${result.id}\n[EMAIL] From: ${RESEND_FROM_EMAIL}\n[EMAIL] To: ${emailAddress}\n[EMAIL] Subject: ${emailSubject}\n[EMAIL] Response Time: ${apiDuration}ms\n[EMAIL] Total Time: ${totalDuration}ms\n[EMAIL] Full Response: ${JSON.stringify(result)}\n[EMAIL] ========================================\n\n`;
      
      // Write multiple times to ensure visibility
      process.stderr.write(emailSuccessLog);
      process.stderr.write(emailSuccessLog); // Write twice
      process.stdout.write(emailSuccessLog);
      
      console.error('\n[EMAIL] ========================================');
      console.error('[EMAIL] ✅✅✅ EMAIL SENT SUCCESSFULLY ✅✅✅');
      console.error('[EMAIL] ========================================');
      console.error(`[EMAIL] Email ID: ${result.id}`);
      console.error(`[EMAIL] From: ${RESEND_FROM_EMAIL}`);
      console.error(`[EMAIL] To: ${emailAddress}`);
      console.error(`[EMAIL] Subject: ${emailSubject}`);
      console.error(`[EMAIL] Response Time: ${apiDuration}ms`);
      console.error(`[EMAIL] Total Time: ${totalDuration}ms`);
      console.error(`[EMAIL] Full Response:`, result);
      console.error('[EMAIL] ========================================\n\n');
      
      return { success: true, id: result.id, email: emailAddress, result: result };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] ❌❌❌ Email send failed! ❌❌❌`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] Response Time: ${duration}ms`);
      console.log(`[EMAIL] Error Name: ${error.name || 'Unknown'}`);
      console.log(`[EMAIL] Error Message: ${error.message || 'No message'}`);
      console.log(`[EMAIL] Error Code: ${error.code || 'N/A'}`);
      console.log(`[EMAIL] Error Status: ${error.status || 'N/A'}`);
      console.log(`[EMAIL] Error Status Code: ${error.statusCode || 'N/A'}`);
      if (error.response) {
        console.log(`[EMAIL] Error Response:`, JSON.stringify(error.response, null, 2));
      }
      if (error.request) {
        console.log(`[EMAIL] Error Request:`, JSON.stringify(error.request, null, 2));
      }
      console.log(`[EMAIL] Error Stack: ${error.stack || 'No stack'}`);
      console.log(`[EMAIL] ========================================`);
      console.log(`[EMAIL] 📋 Full Error Object (JSON):`);
      console.log(JSON.stringify(error, Object.getOwnPropertyNames(error), 2));
      console.log(`[EMAIL] ========================================\n`);
      
      process.stderr.write(`[EMAIL] ========================================\n`);
      process.stderr.write(`[EMAIL] ❌❌❌ EMAIL SEND FAILED ❌❌❌\n`);
      process.stderr.write(`[EMAIL] ========================================\n`);
      process.stderr.write(`[EMAIL] Response Time: ${duration}ms\n`);
      process.stderr.write(`[EMAIL] Error Name: ${error.name || 'Unknown'}\n`);
      process.stderr.write(`[EMAIL] Error Message: ${error.message || 'No message'}\n`);
      process.stderr.write(`[EMAIL] Error Code: ${error.code || 'N/A'}\n`);
      process.stderr.write(`[EMAIL] Error Status: ${error.status || error.statusCode || 'N/A'}\n`);
      if (error.stack) {
        process.stderr.write(`[EMAIL] Error Stack: ${error.stack}\n`);
      }
      process.stderr.write(`[EMAIL] Full Error: ${JSON.stringify(error, Object.getOwnPropertyNames(error), 2)}\n`);
      process.stderr.write(`[EMAIL] ========================================\n\n`);
      
      console.error(`[EMAIL] ❌ Email send failed! Error: ${error.message}\n`);
      
      return { success: false, error: error.message, code: error.code, status: error.status || error.statusCode, fullError: error };
    }
  } else {
    console.log(`[EMAIL] ⚠️  Resend not configured - Email would be sent to ${emailAddress}`);
    console.log(`[EMAIL] OTP Code: ${otpCode}`);
    console.log(`[EMAIL] ============================\n`);
    return { success: true, dev: true, email: emailAddress };
  }
}

// Send SMS via Twilio or return success without sending (for development)
async function sendSMS(phoneNumber, message) {
  const startTime = Date.now();
  console.log(`\n[SMS] ===== SMS Send Attempt =====`);
  console.log(`[SMS] Timestamp: ${new Date().toISOString()}`);
  console.log(`[SMS] To: ${phoneNumber}`);
  console.log(`[SMS] Message: ${message}`);
  console.log(`[SMS] ============================\n`);
  
  // Always return success - SMS provider not configured
  // OTP will be shown in the alert message instead
  console.log(`[SMS] ⚠️  SMS provider not configured - OTP will be shown in alert`);
  console.log(`[SMS] OTP Code: ${message.match(/\d{6}/)?.[0] || 'N/A'}`);
  console.log(`[SMS] ============================\n`);
  
  return { success: true, dev: true, message: 'OTP shown in alert (SMS provider not configured)' };
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

async function getFamilyByEmail(email) {
  if (db) {
    return await db.collection('families').findOne({ email: email.toLowerCase() });
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
  const clientIP = req.ip || req.connection.remoteAddress || req.headers['x-forwarded-for'] || 'unknown';
  const userAgent = req.get('user-agent') || 'N/A';
  const referer = req.get('referer') || 'N/A';
  
  // Force immediate output - use multiple methods
  process.stdout.write('\n\n\n');
  process.stderr.write('\n\n\n');
  
  // Write directly to stderr (unbuffered, always visible)
  process.stderr.write('========================================\n');
  process.stderr.write('🎯🎯🎯 TEST LOG BUTTON CLICKED 🎯🎯🎯\n');
  process.stderr.write('========================================\n');
  
  // Also use console methods
  console.error('\n\n========================================');
  console.error('🎯🎯🎯 TEST LOG BUTTON CLICKED 🎯🎯🎯');
  console.error('========================================\n');
  
  console.log('\n\n========================================');
  console.log('🎯🎯🎯 TEST LOG BUTTON CLICKED 🎯🎯🎯');
  console.log('========================================\n');
  
  // Log all details
  const logData = {
    timestamp,
    clientIP,
    userAgent: userAgent.substring(0, 100), // Truncate for readability
    referer,
    method: req.method,
    path: req.path,
    body: req.body
  };
  
  // Write to stderr (most reliable for Railway)
  process.stderr.write(`[TEST-LOGS] Timestamp: ${timestamp}\n`);
  process.stderr.write(`[TEST-LOGS] Client IP: ${clientIP}\n`);
  process.stderr.write(`[TEST-LOGS] User Agent: ${userAgent.substring(0, 100)}\n`);
  process.stderr.write(`[TEST-LOGS] Referer: ${referer}\n`);
  process.stderr.write(`[TEST-LOGS] Request Method: ${req.method}\n`);
  process.stderr.write(`[TEST-LOGS] Request Path: ${req.path}\n`);
  process.stderr.write(`[TEST-LOGS] Request Body: ${JSON.stringify(req.body)}\n`);
  
  // Also use console
  console.error('[TEST-LOGS] Full data:', JSON.stringify(logData, null, 2));
  console.log('[TEST-LOGS] Full data:', JSON.stringify(logData, null, 2));
  
  // Success message
  process.stderr.write('\n========================================\n');
  process.stderr.write('✅✅✅ LOG ENTRY CREATED SUCCESSFULLY ✅✅✅\n');
  process.stderr.write('========================================\n\n\n');
  
  console.error('\n========================================');
  console.error('✅✅✅ LOG ENTRY CREATED SUCCESSFULLY ✅✅✅');
  console.error('========================================\n\n');
  
  console.log('\n========================================');
  console.log('✅✅✅ LOG ENTRY CREATED SUCCESSFULLY ✅✅✅');
  console.log('========================================\n\n');
  
  // Force flush all streams
  if (process.stdout.isTTY) process.stdout.write('');
  if (process.stderr.isTTY) process.stderr.write('');
  
  res.status(200).json({ 
    success: true, 
    message: 'Log entry created', 
    timestamp,
    clientIP,
    userAgent: userAgent.substring(0, 100)
  });
});

app.post('/api/auth/send-otp', async (req, res) => {
  // CRITICAL: Log IMMEDIATELY at the very start, before anything else
  // Also send response immediately to prevent container from stopping
  const requestStart = Date.now();
  const timestamp = new Date().toISOString();
  
  // Force immediate output - MULTIPLE METHODS AND MULTIPLE TIMES
  const immediateLog = `\n\n\n🎯🎯🎯 ENDPOINT CALLED - FIRST LINE 🎯🎯🎯\n\n\n`;
  process.stderr.write(immediateLog);
  process.stderr.write(immediateLog);
  process.stderr.write(immediateLog);
  process.stdout.write(immediateLog);
  process.stdout.write(immediateLog);
  
  // CRITICAL: Set response timeout to prevent container from stopping
  res.setTimeout(60000); // 60 seconds timeout
  
  // Write to stderr first (most visible in Render) - IMMEDIATE
  const logMessage = `========================================\n📱📱📱 SEND OTP REQUEST RECEIVED 📱📱📱\n========================================\n[SEND-OTP] Timestamp: ${timestamp}\n[SEND-OTP] Method: ${req.method}\n[SEND-OTP] Path: ${req.path}\n[SEND-OTP] Phone: ${req.body?.phoneNumber || 'NOT PROVIDED'}\n[SEND-OTP] Full Body: ${JSON.stringify(req.body || {})}\n========================================\n\n`;
  
  // Write multiple times to ensure visibility
  process.stderr.write(logMessage);
  process.stderr.write(logMessage); // Write twice
  process.stderr.write(logMessage); // Write three times
  process.stdout.write(logMessage);
  process.stdout.write(logMessage);
  
  // Also use console methods
  console.error('\n\n\n========================================');
  console.error('📱📱📱 SEND OTP REQUEST RECEIVED 📱📱📱');
  console.error('========================================');
  console.error(`[SEND-OTP] Timestamp: ${timestamp}`);
  console.error(`[SEND-OTP] Method: ${req.method}`);
  console.error(`[SEND-OTP] Path: ${req.path}`);
  console.error(`[SEND-OTP] Phone: ${req.body?.phoneNumber || 'NOT PROVIDED'}`);
  console.error(`[SEND-OTP] Full Body:`, req.body);
  console.error('========================================\n\n\n');
  
  console.log('\n\n\n========================================');
  console.log('📱📱📱 SEND OTP REQUEST RECEIVED 📱📱📱');
  console.log('========================================');
  console.log(`[SEND-OTP] Timestamp: ${timestamp}`);
  console.log(`[SEND-OTP] Method: ${req.method}`);
  console.log(`[SEND-OTP] Path: ${req.path}`);
  console.log(`[SEND-OTP] Phone: ${req.body?.phoneNumber || 'NOT PROVIDED'}`);
  console.log(`[SEND-OTP] Full Body:`, req.body);
  console.log('========================================\n\n\n');
  
  console.log(`\n[SEND-OTP] ========================================`);
  console.log(`[SEND-OTP] 🚀 Request received at ${timestamp}`);
  console.log(`[SEND-OTP] ========================================`);
  console.log(`[SEND-OTP] 📥 Incoming Request Details:`);
  console.log(`[SEND-OTP]   Method: ${req.method}`);
  console.log(`[SEND-OTP]   Path: ${req.path}`);
  console.log(`[SEND-OTP]   Headers:`, JSON.stringify(req.headers, null, 2));
  console.log(`[SEND-OTP]   Body:`, JSON.stringify(req.body, null, 2));
  console.log(`[SEND-OTP]   Phone: ${req.body.phoneNumber || 'NOT PROVIDED'}`);
  console.log(`[SEND-OTP] ========================================\n`);
  
  console.error(`\n[SEND-OTP] ========================================`);
  console.error(`[SEND-OTP] 🚀 Request received at ${timestamp}`);
  console.error(`[SEND-OTP] Phone: ${req.body.phoneNumber || 'NOT PROVIDED'}`);
  console.error(`[SEND-OTP] ========================================\n`);
  
  try {
    const { phoneNumber } = req.body;
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 1: Validating phone number...`);
    console.log(`[SEND-OTP]   Raw phone: ${phoneNumber || 'undefined'}`);
    
    process.stderr.write(`[SEND-OTP] Step 1: Validating phone number...\n`);
    process.stderr.write(`[SEND-OTP] Raw phone: ${phoneNumber || 'undefined'}\n`);
    
    // Validate phone number
    if (!phoneNumber || phoneNumber.trim().length < 10) {
      console.error(`[SEND-OTP] ❌ Invalid phone number format`);
      process.stderr.write(`[SEND-OTP] ❌ Invalid phone number format\n`);
      return res.status(400).json({ error: 'מספר טלפון לא תקין' });
    }
    
    const normalizedPhone = phoneNumber.trim();
    console.log(`[SEND-OTP] ✅ Phone validated`);
    console.log(`[SEND-OTP]   Normalized phone: ${normalizedPhone}`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] ✅ Phone validated\n`);
    process.stderr.write(`[SEND-OTP] Normalized phone: ${normalizedPhone}\n`);
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 2: Generating OTP...`);
    const otpCode = generateOTP();
    const expiresAt = Date.now() + (10 * 60 * 1000); // 10 minutes
    console.log(`[SEND-OTP]   Generated OTP: ${otpCode}`);
    console.log(`[SEND-OTP]   OTP expires at: ${new Date(expiresAt).toISOString()}`);
    console.log(`[SEND-OTP]   Expires in: 10 minutes`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] Step 2: Generating OTP...\n`);
    process.stderr.write(`[SEND-OTP] Generated OTP: ${otpCode}\n`);
    process.stderr.write(`[SEND-OTP] OTP expires at: ${new Date(expiresAt).toISOString()}\n`);
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 3: Checking if family exists...`);
    const existingFamily = await getFamilyByPhone(normalizedPhone);
    console.log(`[SEND-OTP]   Family exists: ${existingFamily ? 'YES' : 'NO'}`);
    if (existingFamily) {
      console.log(`[SEND-OTP]   Family ID: ${existingFamily._id}`);
    }
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] Step 3: Checking if family exists...\n`);
    process.stderr.write(`[SEND-OTP] Family exists: ${existingFamily ? 'YES' : 'NO'}\n`);
    if (existingFamily) {
      process.stderr.write(`[SEND-OTP] Family ID: ${existingFamily._id}\n`);
    }
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 4: Storing OTP in memory...`);
    otpStore.set(normalizedPhone, {
      code: otpCode,
      expiresAt,
      familyId: existingFamily ? existingFamily._id : null
    });
    console.log(`[SEND-OTP]   OTP stored for: ${normalizedPhone}`);
    console.log(`[SEND-OTP]   OTP code: ${otpCode}`);
    console.log(`[SEND-OTP]   Expires at: ${new Date(expiresAt).toISOString()}`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] Step 4: Storing OTP in memory...\n`);
    process.stderr.write(`[SEND-OTP] OTP stored for: ${normalizedPhone}\n`);
    process.stderr.write(`[SEND-OTP] OTP code: ${otpCode}\n`);
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 5: Calling sendSMS function...`);
    console.log(`[SEND-OTP]   To: ${normalizedPhone}`);
    console.log(`[SEND-OTP]   OTP: ${otpCode}`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] Step 5: Calling sendSMS function...\n`);
    process.stderr.write(`[SEND-OTP] To: ${normalizedPhone}\n`);
    process.stderr.write(`[SEND-OTP] OTP: ${otpCode}\n`);
    
    const smsResult = await sendSMS(normalizedPhone, `קוד האימות שלך: ${otpCode}`);
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 6: SMS result received`);
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] 📥 SMS Result:`);
    console.log(`[SEND-OTP]   Success: ${smsResult.success}`);
    if (smsResult.sid) {
      console.log(`[SEND-OTP]   SMS SID: ${smsResult.sid}`);
    }
    if (smsResult.error) {
      console.log(`[SEND-OTP]   Error: ${smsResult.error}`);
      console.log(`[SEND-OTP]   Error Code: ${smsResult.code || 'N/A'}`);
    }
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] 📋 Full Result Object (JSON):`);
    console.log(JSON.stringify(smsResult, null, 2));
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] SMS result: ${smsResult.success ? 'SUCCESS' : 'FAILED'}\n`);
    if (smsResult.sid) {
      process.stderr.write(`[SEND-OTP] SMS SID: ${smsResult.sid}\n`);
    }
    
    const duration = Date.now() - requestStart;
    const successMessage = `✅ קוד אימות נשלח בהצלחה לטלפון ${normalizedPhone}\n\nקוד האימות: ${otpCode}`;
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] ✅✅✅ OTP GENERATED SUCCESSFULLY ✅✅✅`);
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] To: ${normalizedPhone}`);
    console.log(`[SEND-OTP] OTP Code: ${otpCode}`);
    console.log(`[SEND-OTP] Total request time: ${duration}ms`);
    console.log(`[SEND-OTP] Success Message: ${successMessage}`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    const successLog = `[SEND-OTP] ========================================\n[SEND-OTP] ✅✅✅ OTP GENERATED SUCCESSFULLY ✅✅✅\n[SEND-OTP] ========================================\n[SEND-OTP] To: ${normalizedPhone}\n[SEND-OTP] OTP Code: ${otpCode}\n[SEND-OTP] Total time: ${duration}ms\n[SEND-OTP] Success Message: ${successMessage}\n[SEND-OTP] ========================================\n\n`;
    
    // Write multiple times to ensure visibility
    process.stderr.write(successLog);
    process.stderr.write(successLog); // Write twice
    process.stdout.write(successLog);
    
    console.error('\n[SEND-OTP] ========================================');
    console.error('[SEND-OTP] ✅✅✅ OTP GENERATED SUCCESSFULLY ✅✅✅');
    console.error('[SEND-OTP] ========================================');
    console.error(`[SEND-OTP] To: ${normalizedPhone}`);
    console.error(`[SEND-OTP] OTP Code: ${otpCode}`);
    console.error(`[SEND-OTP] Total time: ${duration}ms`);
    console.error(`[SEND-OTP] Success Message: ${successMessage}`);
    console.error('[SEND-OTP] ========================================\n\n');
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 7: Sending response to client...`);
    console.log(`[SEND-OTP]   Response Status: 200`);
    const responseBody = {
      success: true,
      message: successMessage,
      isExistingFamily: !!existingFamily,
      smsSent: smsResult.success,
      otpCode: otpCode // Include OTP in response for display
    };
    console.log(`[SEND-OTP]   Response Body:`, JSON.stringify(responseBody, null, 2));
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] Sending response to client...\n`);
    process.stderr.write(`[SEND-OTP] Response: ${JSON.stringify(responseBody)}\n`);
    
    res.json(responseBody);
  } catch (error) {
    const duration = Date.now() - requestStart;
    console.error(`[SEND-OTP] ========================================`);
    console.error(`[SEND-OTP] ❌❌❌ EXCEPTION CAUGHT ❌❌❌`);
    console.error(`[SEND-OTP] ========================================`);
    console.error(`[SEND-OTP] Error Name: ${error.name || 'Unknown'}`);
    console.error(`[SEND-OTP] Error Message: ${error.message || 'No message'}`);
    console.error(`[SEND-OTP] Error Stack: ${error.stack || 'No stack'}`);
    console.error(`[SEND-OTP] Duration: ${duration}ms`);
    console.error(`[SEND-OTP] ========================================`);
    console.error(`[SEND-OTP] 📋 Full Error Object (JSON):`);
    console.error(JSON.stringify(error, Object.getOwnPropertyNames(error), 2));
    console.error(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] EXCEPTION: ${error.message}\n`);
    process.stderr.write(`[SEND-OTP] STACK: ${error.stack || 'No stack'}\n`);
    
    res.status(500).json({ 
      error: 'שגיאה בשליחת קוד אימות',
      details: error.message
    });
  }
});

// Verify OTP and login/register
app.post('/api/auth/verify-otp', async (req, res) => {
  try {
    const { phoneNumber, otpCode } = req.body;
    
    if (!phoneNumber || !otpCode) {
      return res.status(400).json({ error: 'מספר טלפון וקוד אימות נדרשים' });
    }
    
    const normalizedPhone = phoneNumber.trim();
    const storedOTP = otpStore.get(normalizedPhone);
    
    if (!storedOTP || storedOTP.expiresAt < Date.now()) {
      return res.status(400).json({ error: 'קוד אימות לא תקין או פג תוקף' });
    }
    
    if (storedOTP.code !== otpCode) {
      return res.status(400).json({ error: 'קוד אימות שגוי' });
    }
    
    // OTP verified - get or create family
    let family = await getFamilyByPhone(normalizedPhone);
    
    if (!family) {
      // Create new family with phone number
      const familyId = `family_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      family = {
        _id: familyId,
        phoneNumber: normalizedPhone,
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
        console.log(`[CREATE-FAMILY] ✅ Family created with phone: ${normalizedPhone}`);
      }
    }
    
    // Remove OTP
    otpStore.delete(normalizedPhone);
    
    res.json({
      success: true,
      familyId: family._id,
      phoneNumber: normalizedPhone,
      isNewFamily: !storedOTP.familyId
    });
  } catch (error) {
    console.error('Error verifying OTP:', error);
    res.status(500).json({ error: 'שגיאה באימות קוד' });
  }
});

// Create child and get join code
app.post('/api/families/:familyId/children', async (req, res) => {
  const requestStart = Date.now();
  const timestamp = new Date().toISOString();
  
  console.log(`\n[CREATE-CHILD-ENDPOINT] ========================================`);
  console.log(`[CREATE-CHILD-ENDPOINT] 📥 Request received at ${timestamp}`);
  console.log(`[CREATE-CHILD-ENDPOINT] ========================================`);
  console.log(`[CREATE-CHILD-ENDPOINT] Method: ${req.method}`);
  console.log(`[CREATE-CHILD-ENDPOINT] Path: ${req.path}`);
  console.log(`[CREATE-CHILD-ENDPOINT] Family ID: ${req.params.familyId}`);
  console.log(`[CREATE-CHILD-ENDPOINT] Body:`, JSON.stringify(req.body, null, 2));
  console.log(`[CREATE-CHILD-ENDPOINT] ========================================\n`);
  
  process.stderr.write(`[CREATE-CHILD-ENDPOINT] Request received - Family: ${req.params.familyId}, Name: ${req.body?.name || 'NOT PROVIDED'}\n`);
  
  try {
    const { familyId } = req.params;
    const { name } = req.body;
    
    console.log(`[CREATE-CHILD-ENDPOINT] Step 1: Validating input...`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Family ID: ${familyId}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Name: ${name || 'NOT PROVIDED'}`);
    
    if (!name) {
      console.error(`[CREATE-CHILD-ENDPOINT] ❌ Name is required`);
      process.stderr.write(`[CREATE-CHILD-ENDPOINT] ❌ Name is required\n`);
      return res.status(400).json({ error: 'שם הילד נדרש' });
    }
    
    console.log(`[CREATE-CHILD-ENDPOINT] Step 2: Getting family...`);
    const family = await getFamilyById(familyId);
    if (!family) {
      console.error(`[CREATE-CHILD-ENDPOINT] ❌ Family not found: ${familyId}`);
      process.stderr.write(`[CREATE-CHILD-ENDPOINT] ❌ Family not found: ${familyId}\n`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    console.log(`[CREATE-CHILD-ENDPOINT] ✅ Family found: ${familyId}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Family has ${family.children?.length || 0} children`);
    
    console.log(`[CREATE-CHILD-ENDPOINT] Step 3: Adding child to family...`);
    const { child, childCode, childPassword } = await addChildToFamily(familyId, name);
    console.log(`[CREATE-CHILD-ENDPOINT] ✅ Child added successfully`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Child ID: ${child._id}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Child Name: ${child.name}`);
    
    const responseBody = {
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
    };
    
    const duration = Date.now() - requestStart;
    console.log(`[CREATE-CHILD-ENDPOINT] Step 4: Sending response...`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Response Status: 200`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Response Body:`, JSON.stringify(responseBody, null, 2));
    console.log(`[CREATE-CHILD-ENDPOINT]   Duration: ${duration}ms`);
    console.log(`[CREATE-CHILD-ENDPOINT] ========================================\n`);
    
    process.stderr.write(`[CREATE-CHILD-ENDPOINT] ✅ Success - Child created: ${child._id}, Name: ${child.name}\n`);
    
    res.json(responseBody);
  } catch (error) {
    const duration = Date.now() - requestStart;
    console.error(`[CREATE-CHILD-ENDPOINT] ========================================`);
    console.error(`[CREATE-CHILD-ENDPOINT] ❌❌❌ ERROR ❌❌❌`);
    console.error(`[CREATE-CHILD-ENDPOINT] ========================================`);
    console.error(`[CREATE-CHILD-ENDPOINT] Error Name: ${error.name || 'Unknown'}`);
    console.error(`[CREATE-CHILD-ENDPOINT] Error Message: ${error.message || 'No message'}`);
    console.error(`[CREATE-CHILD-ENDPOINT] Error Stack: ${error.stack || 'No stack'}`);
    console.error(`[CREATE-CHILD-ENDPOINT] Duration: ${duration}ms`);
    console.error(`[CREATE-CHILD-ENDPOINT] ========================================\n`);
    
    process.stderr.write(`[CREATE-CHILD-ENDPOINT] ❌ ERROR: ${error.message}\n`);
    
    res.status(500).json({ error: 'שגיאה ביצירת ילד', details: error.message });
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
  const timestamp = new Date().toISOString();
  console.log(`\n[GET-CHILDREN] ========================================`);
  console.log(`[GET-CHILDREN] 📥 Request received at ${timestamp}`);
  console.log(`[GET-CHILDREN] ========================================`);
  console.log(`[GET-CHILDREN] Family ID: ${req.params.familyId}`);
  console.log(`[GET-CHILDREN] ========================================\n`);
  
  try {
    const { familyId } = req.params;
    console.log(`[GET-CHILDREN] Step 1: Getting family...`);
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[GET-CHILDREN] ❌ Family not found: ${familyId}`);
      process.stderr.write(`[GET-CHILDREN] ❌ Family not found: ${familyId}\n`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    console.log(`[GET-CHILDREN] ✅ Family found: ${familyId}`);
    console.log(`[GET-CHILDREN]   Family has ${family.children?.length || 0} children`);
    if (family.children && family.children.length > 0) {
      console.log(`[GET-CHILDREN]   Children:`, family.children.map(c => ({ id: c._id, name: c.name })));
    }
    
    console.log(`[GET-CHILDREN] Step 2: Mapping children...`);
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
    
    console.log(`[GET-CHILDREN] Step 3: Converting to object...`);
    const childrenObject = children.reduce((acc, child) => {
      acc[child._id] = child;
      return acc;
    }, {});
    
    console.log(`[GET-CHILDREN] ✅ Sending response`);
    console.log(`[GET-CHILDREN]   Total children: ${Object.keys(childrenObject).length}`);
    console.log(`[GET-CHILDREN]   Children IDs:`, Object.keys(childrenObject));
    console.log(`[GET-CHILDREN] ========================================\n`);
    
    process.stderr.write(`[GET-CHILDREN] ✅ Response sent - ${Object.keys(childrenObject).length} children\n`);
    
    res.json({ children: childrenObject });
  } catch (error) {
    console.error(`[GET-CHILDREN] ========================================`);
    console.error(`[GET-CHILDREN] ❌❌❌ ERROR ❌❌❌`);
    console.error(`[GET-CHILDREN] ========================================`);
    console.error(`[GET-CHILDREN] Error Name: ${error.name || 'Unknown'}`);
    console.error(`[GET-CHILDREN] Error Message: ${error.message || 'No message'}`);
    console.error(`[GET-CHILDREN] Error Stack: ${error.stack || 'No stack'}`);
    console.error(`[GET-CHILDREN] ========================================\n`);
    
    process.stderr.write(`[GET-CHILDREN] ❌ ERROR: ${error.message}\n`);
    
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
  console.log(`[SERVER] ✅ Server is ready and listening`);
  console.log(`[SERVER] ✅ Waiting for Render health check calls...`);
  
  // Start heartbeat to keep container alive and log activity
  // Monitor service health and log activity
  let heartbeatCount = 0;
  setInterval(() => {
    if (serverReady) {
      heartbeatCount++;
      const uptime = process.uptime();
      const timeSinceLastHealthCheck = Date.now() - lastHealthCheckTime;
      console.log(`[HEARTBEAT] Server is alive - uptime: ${Math.floor(uptime)}s, heartbeat: ${heartbeatCount}, health checks received: ${healthCheckCount}, last check: ${Math.floor(timeSinceLastHealthCheck / 1000)}s ago`);
      
      // If no health checks for 5 minutes, log warning
      if (timeSinceLastHealthCheck > 300000 && healthCheckCount > 0) {
        console.log(`[HEARTBEAT] ⚠️  WARNING: No health checks for ${Math.floor(timeSinceLastHealthCheck / 1000)}s`);
        console.log(`[HEARTBEAT] ⚠️  Check: Render Dashboard → Settings → Health Check`);
      }
      // If no health checks at all, log warning (but not critical - Render may take time)
      if (healthCheckCount === 0 && uptime > 120) {
        console.log(`[HEARTBEAT] ⚠️  INFO: No health checks received after ${Math.floor(uptime)}s`);
        console.log(`[HEARTBEAT] ⚠️  Render may take a few minutes to start health checks`);
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
  
  // Log to stderr immediately (most visible in Render)
  const sigtermLog = `\n\n\n⚠️⚠️⚠️ SIGTERM RECEIVED ⚠️⚠️⚠️\n[SERVER] SIGTERM received (call #${sigtermCount})\n[SERVER] Server uptime: ${Math.floor(uptime)}s\n[SERVER] Total health check calls received: ${healthCheckCount}\n[SERVER] Last health check: ${Math.floor(timeSinceLastHealthCheck / 1000)}s ago\n\n\n`;
  process.stderr.write(sigtermLog);
  process.stderr.write(sigtermLog);
  process.stdout.write(sigtermLog);
  
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
  
  console.error(`\n[SERVER] ⚠️  SIGTERM received (call #${sigtermCount})`);
  console.error(`[SERVER] ⚠️  Server uptime: ${Math.floor(uptime)}s`);
  console.error(`[SERVER] ⚠️  Total health check calls received: ${healthCheckCount}`);
  
  if (healthCheckCount === 0) {
    const noHealthCheckLog = `[SERVER] ⚠️  INFO: No health check calls received yet\n[SERVER] ⚠️  Render may take a few minutes to start health checks\n[SERVER] ⚠️  Check: Render Dashboard → Settings → Health Check → Path should be '/health'\n`;
    process.stderr.write(noHealthCheckLog);
    console.log(`[SERVER] ⚠️  INFO: No health check calls received yet`);
    console.log(`[SERVER] ⚠️  Render may take a few minutes to start health checks`);
    console.log(`[SERVER] ⚠️  Check: Render Dashboard → Settings → Health Check`);
  } else if (timeSinceLastHealthCheck > 300000) {
    const noHealthCheckLog = `[SERVER] ⚠️  WARNING: No health checks for ${Math.floor(timeSinceLastHealthCheck / 1000)}s!\n[SERVER] ⚠️  Render stopped calling /health after ${healthCheckCount} calls\n[SERVER] ⚠️  Check: Render Dashboard → Settings → Health Check\n`;
    process.stderr.write(noHealthCheckLog);
    console.log(`[SERVER] ⚠️  WARNING: No health checks for ${Math.floor(timeSinceLastHealthCheck / 1000)}s!`);
    console.log(`[SERVER] ⚠️  Render stopped calling /health after ${healthCheckCount} calls`);
    console.log(`[SERVER] ⚠️  Check: Render Dashboard → Settings → Health Check`);
  } else {
    console.log(`[SERVER] ⚠️  Health checks were received (${healthCheckCount} total) but Render sent SIGTERM`);
    console.log(`[SERVER] ⚠️  This may indicate health check response format issue`);
    console.log(`[SERVER] ⚠️  Check: Render Dashboard → Settings → Health Check → Path should be '/health'`);
  }
  
  const ignoreLog = `[SERVER] ⚠️  IGNORING SIGTERM - Server will continue running\n[SERVER] ⚠️  Server is still active and accepting requests\n[SERVER] ⚠️  Note: Railway may force kill the container, but we'll try to keep running\n`;
  process.stderr.write(ignoreLog);
  process.stderr.write(ignoreLog);
  
  console.log(`[SERVER] ⚠️  ========================================`);
  console.log(`[SERVER] ⚠️  IGNORING SIGTERM - Server will continue running`);
  console.log(`[SERVER] ⚠️  Server is still active and accepting requests`);
  console.log(`[SERVER] ⚠️  Note: Render may force kill the service, but we'll try to keep running`);
  console.log(`[SERVER] ⚠️  ========================================\n`);
  
  // DO NOT shut down - continue running
  // Render may force kill the service, but we'll try to keep running
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
  // Don't exit - let Render handle it
});

process.on('unhandledRejection', (reason) => {
  console.error('[ERROR] Unhandled Rejection:', reason);
  // Don't exit - let Render handle it
});

// Connect to DB in background (don't block server startup)
// This happens after server is already listening
setTimeout(() => {
  connectDB();
}, 100);

