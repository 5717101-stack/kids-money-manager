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

// Twilio configuration (for SMS OTP)
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

// MongoDB client with connection pooling for better performance
let mongoClient = null;

async function connectDB() {
  try {
    // Use connection pooling for better performance
    // maxPoolSize: 10 - allows up to 10 concurrent connections
    // minPoolSize: 2 - maintains at least 2 connections ready
    // maxIdleTimeMS: 30000 - closes idle connections after 30s
    mongoClient = new MongoClient(MONGODB_URI, {
      maxPoolSize: 20, // Increased for better concurrency
      minPoolSize: 5, // Keep more connections ready
      maxIdleTimeMS: 60000, // Keep connections longer (1 minute)
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
      connectTimeoutMS: 10000, // 10 seconds to connect
    });
    await mongoClient.connect();
    db = mongoClient.db();
    console.log('[DB] Connected to MongoDB with connection pooling');
    console.log('[DB] Pool settings: maxPoolSize=20, minPoolSize=5');
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
  
  // Check if Twilio is configured
  if (twilioClient && TWILIO_PHONE_NUMBER) {
    try {
      console.log(`[SMS] 📤 Attempting to send SMS via Twilio...`);
      console.log(`[SMS] From: ${TWILIO_PHONE_NUMBER}`);
      console.log(`[SMS] To: ${phoneNumber}`);
      
      const result = await twilioClient.messages.create({
        body: message,
        from: TWILIO_PHONE_NUMBER,
        to: phoneNumber
      });
      
      const duration = Date.now() - startTime;
      console.log(`[SMS] ✅ SMS sent successfully via Twilio!`);
      console.log(`[SMS] SID: ${result.sid}`);
      console.log(`[SMS] Status: ${result.status}`);
      console.log(`[SMS] Duration: ${duration}ms`);
      console.log(`[SMS] ============================\n`);
      
      return { 
        success: true, 
        sid: result.sid, 
        status: result.status,
        message: 'SMS sent successfully via Twilio'
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[SMS] ❌ Failed to send SMS via Twilio!`);
      console.error(`[SMS] Error: ${error.message}`);
      console.error(`[SMS] Error Code: ${error.code || 'N/A'}`);
      console.error(`[SMS] Duration: ${duration}ms`);
      console.error(`[SMS] ============================\n`);
      
      return { 
        success: false, 
        error: error.message, 
        code: error.code,
        message: 'Failed to send SMS via Twilio'
      };
    }
  } else {
    // Twilio not configured - return success for development
    console.log(`[SMS] ⚠️  Twilio not configured - SMS will not be sent`);
    console.log(`[SMS] OTP Code: ${message.match(/\d{6}/)?.[0] || 'N/A'}`);
    console.log(`[SMS] ============================\n`);
    
    return { 
      success: true, 
      dev: true, 
      message: 'OTP shown in alert (Twilio not configured)' 
    };
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
    // Create indexes for performance optimization
    if (db) {
      // Main indexes
      await db.collection('families').createIndex({ phoneNumber: 1 }, { unique: true });
      await db.collection('families').createIndex({ _id: 1 }); // Already exists but ensure it
      await db.collection('families').createIndex({ 'children._id': 1 });
      await db.collection('families').createIndex({ 'children.phoneNumber': 1 }); // For child phone lookup
      await db.collection('families').createIndex({ 'additionalParents.phoneNumber': 1 }); // For additional parent lookup
      // Index for transaction queries (by date, type, childId)
      await db.collection('families').createIndex({ 'children.transactions.date': -1 }); // For sorting transactions
      await db.collection('families').createIndex({ 'children.transactions.type': 1 }); // For filtering by type
      await db.collection('otpCodes').createIndex({ phoneNumber: 1 });
      await db.collection('otpCodes').createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });
      await db.collection('otpCodes').createIndex({ familyId: 1 }); // For OTP family lookup
    }
    console.log('[DB] Indexes created');
  } catch (error) {
    console.error('[DB] Error initializing:', error.message);
  }
}

// Helper functions
// Normalize phone number - ensure it has country code
function normalizePhoneNumber(phoneNumber, defaultCountryCode = '+972') {
  if (!phoneNumber) return phoneNumber;
  const trimmed = phoneNumber.trim();
  
  // If already starts with +, check if it has double country code (e.g., +972054...)
  if (trimmed.startsWith('+')) {
    // If it's +9720..., remove the 0 after country code
    if (trimmed.startsWith('+9720') && trimmed.length > 5) {
      return '+972' + trimmed.substring(5); // +972054... -> +97254...
    }
    return trimmed;
  }
  
  // If starts with 0, replace with country code
  if (trimmed.startsWith('0')) {
    return defaultCountryCode + trimmed.substring(1);
  }
  
  // Otherwise, add country code
  return defaultCountryCode + trimmed;
}

// Cache for family lookups (5 minute TTL)
const familyCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function getFamilyByPhone(phoneNumber) {
  if (!phoneNumber) return null;
  
  const normalized = normalizePhoneNumber(phoneNumber);
  
  // Check cache first
  const cacheKey = `phone:${normalized}`;
  const cached = familyCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    console.log(`[GET-FAMILY-BY-PHONE] Cache hit for: ${normalized}`);
    return cached.data;
  }
  
  console.log(`[GET-FAMILY-BY-PHONE] Searching for phone: ${phoneNumber}, normalized: ${normalized}`);
  
  if (db) {
    try {
      // First try direct lookup by main phone (indexed)
      // Exclude transactions to prevent loading huge documents
      let family = await db.collection('families').findOne(
        { phoneNumber: normalized },
        {
          projection: {
            // Include all fields, but we'll handle transactions separately if needed
          }
        }
      );
      if (family) {
        console.log(`[GET-FAMILY-BY-PHONE] Found family ${family._id} via main parent (indexed)`);
        familyCache.set(cacheKey, { data: family, timestamp: Date.now() });
        return family;
      }
      
      // Try to find by additional parents using aggregation (more efficient than loading all)
      family = await db.collection('families').findOne(
        { 'additionalParents.phoneNumber': normalized },
        {
          projection: {
            // Include all fields
          }
        }
      );
      if (family) {
        console.log(`[GET-FAMILY-BY-PHONE] Found family ${family._id} via additional parent (indexed)`);
        familyCache.set(cacheKey, { data: family, timestamp: Date.now() });
        return family;
      }
    } catch (error) {
      console.error(`[GET-FAMILY-BY-PHONE] Error loading family by phone ${normalized}:`, error.message);
      // Try without transactions if document is too large
      try {
        let family = await db.collection('families').findOne(
          { phoneNumber: normalized },
          { projection: { 'children.transactions': 0 } }
        );
        if (family) {
          console.log(`[GET-FAMILY-BY-PHONE] Loaded family without transactions due to size`);
          familyCache.set(cacheKey, { data: family, timestamp: Date.now() });
          return family;
        }
      } catch (retryError) {
        console.error(`[GET-FAMILY-BY-PHONE] Failed to load family even without transactions:`, retryError.message);
      }
    }
    
    // Fallback: if normalization doesn't match exactly, do a limited scan
    // Only check first 100 families (should be enough for most cases)
    const allFamilies = await db.collection('families').find({}).limit(100).toArray();
    
    for (const fam of allFamilies) {
      // Check main parent phone (normalize for comparison)
      if (fam.phoneNumber) {
        const mainPhoneNormalized = normalizePhoneNumber(fam.phoneNumber);
        if (mainPhoneNormalized === normalized) {
          console.log(`[GET-FAMILY-BY-PHONE] Found family ${fam._id} via main parent (fallback)`);
          familyCache.set(cacheKey, { data: fam, timestamp: Date.now() });
          return fam;
        }
      }
      
      // Check additional parents (normalize all for comparison)
      if (fam.additionalParents && Array.isArray(fam.additionalParents)) {
        for (const parent of fam.additionalParents) {
          if (parent.phoneNumber) {
            const parentPhoneNormalized = normalizePhoneNumber(parent.phoneNumber);
            if (parentPhoneNormalized === normalized) {
              console.log(`[GET-FAMILY-BY-PHONE] Found family ${fam._id} via additional parent ${parent.name} (fallback)`);
              familyCache.set(cacheKey, { data: fam, timestamp: Date.now() });
              return fam;
            }
          }
        }
      }
    }
  }
  
  console.log(`[GET-FAMILY-BY-PHONE] No family found for phone: ${normalized}`);
  return null;
}

async function getFamilyByEmail(email) {
  if (db) {
    return await db.collection('families').findOne({ email: email.toLowerCase() });
  }
  return null;
}

// Cache for getFamilyById (2 minute TTL)
const familyByIdCache = new Map();
const FAMILY_BY_ID_CACHE_TTL = 2 * 60 * 1000; // 2 minutes

async function getFamilyById(familyId) {
  if (!familyId) return null;
  
  // Check cache first
  const cacheKey = `id:${familyId}`;
  const cached = familyByIdCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < FAMILY_BY_ID_CACHE_TTL) {
    return cached.data;
  }
  
  if (db) {
    try {
      // Use projection to exclude transactions initially (they're loaded separately)
      // This prevents loading huge documents that exceed MongoDB's 16MB limit
      const family = await db.collection('families').findOne(
        { _id: familyId },
        {
          projection: {
            // Include all fields except transactions (they're loaded separately)
            // We'll add transactions back if needed, but for most operations we don't need them
          }
        }
      );
      
      if (family) {
        // Check document size (approximate)
        const docSize = JSON.stringify(family).length;
        if (docSize > 15 * 1024 * 1024) { // 15MB warning
          console.warn(`[GET-FAMILY-BY-ID] ⚠️  Large document detected: ${(docSize / 1024 / 1024).toFixed(2)}MB for family ${familyId}`);
        }
        
        // Cache the result
        familyByIdCache.set(cacheKey, { data: family, timestamp: Date.now() });
      }
      return family;
    } catch (error) {
      console.error(`[GET-FAMILY-BY-ID] Error loading family ${familyId}:`, error.message);
      // If document is too large, try to load without transactions
      try {
        const family = await db.collection('families').findOne(
          { _id: familyId },
          {
            projection: {
              'children.transactions': 0 // Exclude transactions
            }
          }
        );
        if (family) {
          console.log(`[GET-FAMILY-BY-ID] Loaded family without transactions due to size`);
          familyByIdCache.set(cacheKey, { data: family, timestamp: Date.now() });
        }
        return family;
      } catch (retryError) {
        console.error(`[GET-FAMILY-BY-ID] Failed to load family even without transactions:`, retryError.message);
        return null;
      }
    }
  }
  return null;
}

// Function to invalidate cache when family is updated
function invalidateFamilyCache(familyId) {
  if (familyId) {
    familyByIdCache.delete(`id:${familyId}`);
    // Also clear phone-based cache entries (we don't know which phone, so clear all)
    // In production, you might want to track phone->familyId mapping
    familyCache.clear();
  }
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

async function addChildToFamily(familyId, childName, phoneNumber) {
  console.log(`\n[ADD-CHILD] ===== Adding Child to Family =====`);
  console.log(`[ADD-CHILD] Family ID: ${familyId}`);
  console.log(`[ADD-CHILD] Child Name: ${childName}`);
  console.log(`[ADD-CHILD] Child Phone (raw): ${phoneNumber}`);
  
  const childId = `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
  
  console.log(`[ADD-CHILD] Child ID: ${childId}`);
  console.log(`[ADD-CHILD] Phone Number (normalized): ${normalizedPhone}`);
  
  // Check if phone number already exists (as parent or child)
  if (db) {
    // Check if phone number belongs to a parent (try both formats)
    const existingFamilyByPhone = await getFamilyByPhone(normalizedPhone);
    if (existingFamilyByPhone) {
      console.error(`[ADD-CHILD] ❌ Phone number already in use by a parent: ${normalizedPhone}`);
      throw new Error('מספר טלפון זה כבר בשימוש על ידי הורה');
    }
    
    // Check if phone number belongs to another child using indexed query (much faster)
    if (db) {
      const existingFamily = await db.collection('families').findOne({
        $or: [
          { phoneNumber: normalizedPhone },
          { 'children.phoneNumber': normalizedPhone },
          { 'additionalParents.phoneNumber': normalizedPhone }
        ]
      });
      
      if (existingFamily) {
        // Double-check by normalizing
        if (existingFamily.phoneNumber && normalizePhoneNumber(existingFamily.phoneNumber) === normalizedPhone) {
          throw new Error('מספר טלפון זה כבר בשימוש על ידי הורה');
        }
        if (existingFamily.children) {
          for (const ch of existingFamily.children) {
            if (ch.phoneNumber && normalizePhoneNumber(ch.phoneNumber) === normalizedPhone) {
              console.error(`[ADD-CHILD] ❌ Phone number already in use by a child: ${normalizedPhone} (found in family ${existingFamily._id}, child ${ch._id})`);
              throw new Error('מספר טלפון זה כבר בשימוש על ידי ילד אחר');
            }
          }
        }
        if (existingFamily.additionalParents) {
          for (const parent of existingFamily.additionalParents) {
            if (parent.phoneNumber && normalizePhoneNumber(parent.phoneNumber) === normalizedPhone) {
              throw new Error('מספר טלפון זה כבר בשימוש על ידי הורה');
            }
          }
        }
      }
    }
  }
  
  const child = {
    _id: childId,
    name: childName,
    phoneNumber: normalizedPhone,
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
  
  if (db) {
    // First, verify the family exists and get it
    const family = await getFamilyById(familyId);
    if (!family) {
      console.error(`[ADD-CHILD] ❌ Family not found: ${familyId}`);
      throw new Error('משפחה לא נמצאה');
    }
    
    console.log(`[ADD-CHILD] Family found, current children count: ${family.children?.length || 0}`);
    
    // Add child to family
    await db.collection('families').updateOne(
      { _id: familyId },
      { 
        $push: { children: child }
      }
    );
    console.log(`[ADD-CHILD] ✅ Child saved to database`);
    
    // Invalidate cache
    invalidateFamilyCache(familyId);
    
    // Update categories to include new child
    if (family.categories && family.categories.length > 0) {
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
    
    // Verify the child was added
    const updatedFamily = await getFamilyById(familyId);
    console.log(`[ADD-CHILD] Verification: Family now has ${updatedFamily?.children?.length || 0} children`);
    if (updatedFamily?.children) {
      const addedChild = updatedFamily.children.find(c => c._id === childId);
      if (addedChild) {
        console.log(`[ADD-CHILD] ✅ Child verified in database: ${addedChild.name} (${addedChild._id})`);
      } else {
        console.error(`[ADD-CHILD] ❌ Child not found in database after insertion!`);
      }
    }
  } else {
    console.log(`[ADD-CHILD] ⚠️  Using in-memory storage (no DB)`);
  }
  
  console.log(`[ADD-CHILD] ============================\n`);
  return { child, phoneNumber: normalizedPhone };
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
        const isCorrectTime = hour === allowanceHour && minute >= allowanceMinute;
        shouldProcess = isCorrectDay && isCorrectTime;
        
        if (shouldProcess) {
          // Check if allowance was already paid today (same day and same hour)
          const todayStart = new Date(now);
          todayStart.setHours(0, 0, 0, 0);
          
          const recentAllowance = (child.transactions || []).find(t => {
            if (!t || t.type !== 'deposit') return false;
            const tDate = new Date(t.date);
            return (t.description === 'דמי כיס שבועיים' || t.description === 'דמי כיס חודשיים') &&
                   tDate >= todayStart &&
                   tDate.getHours() === hour;
          });
          
          if (recentAllowance) {
            console.log(`⏭️ Skipping allowance for ${child.name} - already paid today at ${recentAllowance.date}`);
            continue;
          }
        }
      } else if (allowanceType === 'monthly') {
        const isCorrectDay = dayOfMonth === allowanceDay;
        const isCorrectTime = hour === allowanceHour && minute >= allowanceMinute;
        shouldProcess = isCorrectDay && isCorrectTime;
        
        if (shouldProcess) {
          // Check if allowance was already paid today (same day and same hour)
          const todayStart = new Date(now);
          todayStart.setHours(0, 0, 0, 0);
          
          const recentAllowance = (child.transactions || []).find(t => {
            if (!t || t.type !== 'deposit') return false;
            const tDate = new Date(t.date);
            return (t.description === 'דמי כיס שבועיים' || t.description === 'דמי כיס חודשיים') &&
                   tDate >= todayStart &&
                   tDate.getHours() === hour;
          });
          
          if (recentAllowance) {
            console.log(`⏭️ Skipping allowance for ${child.name} - already paid today at ${recentAllowance.date}`);
            continue;
          }
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
        
        // Calculate balance increment instead of recalculating all
        const balanceChange = child.weeklyAllowance;
        
        // Update child in family using atomic operations
        if (db) {
          await db.collection('families').updateOne(
            { _id: familyId, 'children._id': child._id },
            { 
              $push: { 'children.$.transactions': transaction },
              $inc: { 'children.$.balance': balanceChange },
              $set: { 'children.$.lastAllowancePayment': new Date().toISOString() }
            }
          );
          invalidateFamilyCache(familyId);
        }
        
        console.log(`✅ Added ${allowanceType} allowance of ${child.weeklyAllowance} to ${child.name} in family ${familyId} at ${new Date().toISOString()}`);
      }
    }
  } catch (error) {
    console.error('Error processing allowances:', error);
  }
}

// Process daily interest for a family (calculated daily, but rate is weekly)
async function processInterestForFamily(familyId) {
  try {
    const family = await getFamilyById(familyId);
    if (!family || !family.children) return;

    const now = new Date();
    
    for (const child of family.children) {
      if (!child.weeklyInterestRate || child.weeklyInterestRate <= 0) continue;
      if (!child.balance || child.balance <= 0) continue;

      const lastCalcDate = child.lastInterestCalculation ? new Date(child.lastInterestCalculation) : null;
      const oneDayAgo = new Date(now);
      oneDayAgo.setDate(now.getDate() - 1);
      oneDayAgo.setHours(0, 0, 0, 0);

      // Calculate interest daily (weekly rate divided by 7)
      const dailyInterestRate = child.weeklyInterestRate / 7;
      
      // Only calculate if it's been at least 1 day since last calculation
      if (!lastCalcDate || lastCalcDate <= oneDayAgo) {
        const interestAmount = (child.balance || 0) * (dailyInterestRate / 100);
        if (interestAmount > 0) {
          const newBalance = (child.balance || 0) + interestAmount;
          const newTotalInterestEarned = (child.totalInterestEarned || 0) + interestAmount;

          const transaction = {
            id: `interest_${Date.now()}_${child._id}`,
            date: new Date().toISOString(),
            type: 'deposit',
            amount: interestAmount,
            description: `ריבית יומית (${child.weeklyInterestRate}% שבועי)`,
            category: null,
            childId: child._id
          };

          // Use atomic operations for better performance
          await db.collection('families').updateOne(
            { _id: familyId, 'children._id': child._id },
            {
              $push: { 'children.$.transactions': transaction },
              $inc: { 
                'children.$.balance': interestAmount,
                'children.$.totalInterestEarned': interestAmount
              },
              $set: {
                'children.$.lastInterestCalculation': new Date().toISOString()
              }
            }
          );
          invalidateFamilyCache(familyId);
          
          console.log(`✅ Added ${interestAmount.toFixed(2)} daily interest (${dailyInterestRate.toFixed(4)}%) to ${child.name} in family ${familyId}`);
        }
      }
    }
  } catch (error) {
    console.error('Error processing interest:', error);
  }
}

// Check allowances and interest every minute
setInterval(async () => {
  if (db) {
    const families = await db.collection('families').find({}).toArray();
    for (const family of families) {
      await processAllowancesForFamily(family._id);
      await processInterestForFamily(family._id);
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
    
    // Normalize phone number to ensure consistent format
    const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
    console.log(`[SEND-OTP] ✅ Phone validated`);
    console.log(`[SEND-OTP]   Raw phone: ${phoneNumber.trim()}`);
    console.log(`[SEND-OTP]   Normalized phone: ${normalizedPhone}`);
    console.log(`[SEND-OTP] ========================================\n`);
    
    process.stderr.write(`[SEND-OTP] ✅ Phone validated\n`);
    process.stderr.write(`[SEND-OTP] Raw phone: ${phoneNumber.trim()}\n`);
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
    console.log(`[SEND-OTP] Step 3: Checking if phone number exists (family or child)...`);
    
    // First check if phone number belongs to a child (normalize all children's phones for comparison)
    let child = null;
    let existingFamily = null;
    
    if (db) {
      // Use indexed query first (much faster)
      const familyWithChild = await db.collection('families').findOne({
        'children.phoneNumber': normalizedPhone
      });
      
      if (familyWithChild && familyWithChild.children) {
        for (const ch of familyWithChild.children) {
          if (ch.phoneNumber) {
            const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
            console.log(`[SEND-OTP]   Checking child ${ch.name}: raw="${ch.phoneNumber}", normalized="${childPhoneNormalized}" vs search="${normalizedPhone}"`);
            if (childPhoneNormalized === normalizedPhone) {
              child = ch;
              existingFamily = familyWithChild;
              console.log(`[SEND-OTP]   ✅ Found child (indexed): ${child.name} (${child._id}) in family ${existingFamily._id}`);
              process.stderr.write(`[SEND-OTP] ✅ Found child: ${child.name} in family ${existingFamily._id}\n`);
              break;
            }
          }
        }
      }
      
      // Fallback: limited scan if indexed query didn't work
      if (!child) {
        const allFamilies = await db.collection('families').find({}).limit(50).toArray();
        console.log(`[SEND-OTP] Searching through ${allFamilies.length} families for child with phone: ${normalizedPhone} (fallback)`);
        for (const fam of allFamilies) {
          if (fam.children && Array.isArray(fam.children)) {
            for (const ch of fam.children) {
              if (ch.phoneNumber) {
                const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
                if (childPhoneNormalized === normalizedPhone) {
                  child = ch;
                  existingFamily = fam;
                  console.log(`[SEND-OTP]   ✅ Found child (fallback): ${child.name} (${child._id}) in family ${existingFamily._id}`);
                  break;
                }
              }
            }
            if (child) break;
          }
        }
      }
      if (!child) {
        console.log(`[SEND-OTP]   ℹ️  No child found with phone: ${normalizedPhone}`);
      }
    }
    
    // If not a child, check if it's a family phone number
    if (!child) {
      existingFamily = await getFamilyByPhone(normalizedPhone);
      if (existingFamily) {
        console.log(`[SEND-OTP]   ✅ Found family: ${existingFamily._id}`);
        process.stderr.write(`[SEND-OTP] ✅ Found family: ${existingFamily._id}\n`);
      } else {
        console.log(`[SEND-OTP]   ℹ️  New user - will create family after OTP verification`);
        process.stderr.write(`[SEND-OTP] ℹ️  New user - will create family after OTP verification\n`);
      }
    }
    
    console.log(`[SEND-OTP] ========================================\n`);
    
    console.log(`[SEND-OTP] ========================================`);
    console.log(`[SEND-OTP] Step 4: Storing OTP in memory...`);
    otpStore.set(normalizedPhone, {
      code: otpCode,
      expiresAt,
      familyId: existingFamily ? existingFamily._id : null,
      isChild: !!child,
      childId: child ? child._id : null
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
    
    // Format SMS for iOS AutoFill - must include the code in a recognizable format
    // iOS recognizes patterns like: "Your code is: 123456" or "123456 is your code"
    const smsMessage = `${otpCode} הוא קוד האימות שלך. קוד זה תקף ל-10 דקות.`;
    const smsResult = await sendSMS(normalizedPhone, smsMessage);
    
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
    
    // Normalize phone number to ensure consistent format (same as in send-otp)
    const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
    let storedOTP = otpStore.get(normalizedPhone);
    
    // Also try non-normalized version (for backward compatibility with old OTPs)
    if (!storedOTP) {
      const nonNormalized = phoneNumber.trim();
      storedOTP = otpStore.get(nonNormalized);
      if (storedOTP) {
        console.log(`[VERIFY-OTP] Found OTP with non-normalized phone, using normalized: ${normalizedPhone}`);
      }
    }
    
    if (!storedOTP || storedOTP.expiresAt < Date.now()) {
      return res.status(400).json({ error: 'קוד אימות לא תקין או פג תוקף' });
    }
    
    if (storedOTP.code !== otpCode) {
      return res.status(400).json({ error: 'קוד אימות שגוי' });
    }
    
    // Use information from OTP store (set during send-otp)
    let child = null;
    let family = null;
    
    // First, check if OTP store indicates this is a child
    if (storedOTP.isChild && storedOTP.childId && storedOTP.familyId) {
      console.log(`[VERIFY-OTP] ℹ️  OTP store indicates this is a child: ${storedOTP.childId} in family ${storedOTP.familyId}`);
      family = await getFamilyById(storedOTP.familyId);
      if (family) {
        child = family.children?.find(c => c._id === storedOTP.childId);
        if (child) {
          console.log(`[VERIFY-OTP] ✅ Found child from OTP store: ${child.name} (${child._id}) in family ${family._id}`);
        }
      }
    }
    
    // If not found from OTP store, check database directly using indexed query
    if (!child && db) {
      // Use indexed query to find child by phone number (much faster)
      const familyWithChild = await db.collection('families').findOne({
        'children.phoneNumber': normalizedPhone
      });
      
      if (familyWithChild && familyWithChild.children) {
        for (const ch of familyWithChild.children) {
          if (ch.phoneNumber) {
            const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
            if (childPhoneNormalized === normalizedPhone) {
              child = ch;
              family = familyWithChild;
              console.log(`[VERIFY-OTP] ✅ Found child from database (indexed): ${child.name} (${child._id}) in family ${family._id}`);
              break;
            }
          }
        }
      }
      
      // Fallback: if indexed query didn't work, try limited scan (only first 50 families)
      if (!child) {
        const allFamilies = await db.collection('families').find({}).limit(50).toArray();
        for (const fam of allFamilies) {
          if (fam.children && Array.isArray(fam.children)) {
            for (const ch of fam.children) {
              if (ch.phoneNumber) {
                const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
                if (childPhoneNormalized === normalizedPhone) {
                  child = ch;
                  family = fam;
                  console.log(`[VERIFY-OTP] ✅ Found child from database (fallback): ${child.name} (${child._id}) in family ${family._id}`);
                  break;
                }
              }
            }
            if (child) break;
          }
        }
      }
    }
    
    // If not a child, check if it's a parent's phone number (main or additional)
    if (!child) {
      // Check if storedOTP has familyId (from send-otp)
      if (storedOTP.familyId) {
        family = await getFamilyById(storedOTP.familyId);
        if (family) {
          console.log(`[VERIFY-OTP] ✅ Found family from OTP store: ${family._id}`);
        }
      }
      
      // If not found from OTP store, check database (this now checks both main and additional parents)
      if (!family) {
        family = await getFamilyByPhone(normalizedPhone);
        if (family) {
          console.log(`[VERIFY-OTP] ✅ Found family from database: ${family._id}`);
          // Check if this is an additional parent (normalize for comparison)
          if (family.additionalParents && Array.isArray(family.additionalParents)) {
            for (const parent of family.additionalParents) {
              if (parent.phoneNumber) {
                const parentPhoneNormalized = normalizePhoneNumber(parent.phoneNumber);
                if (parentPhoneNormalized === normalizedPhone) {
                  console.log(`[VERIFY-OTP] ℹ️  This is an additional parent: ${parent.name}`);
                  break;
                }
              }
            }
          }
        }
      }
      
      // Only create new family if it's not a child and not an existing family (main or additional parent)
      if (!family) {
        console.log(`[VERIFY-OTP] ℹ️  No existing family or child found - creating new family`);
        const familyId = `family_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        family = {
          _id: familyId,
          phoneNumber: normalizedPhone, // Store normalized phone number
          parentName: 'הורה1', // Default parent name
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
    }
    
    // Check if this is an additional parent (normalize all for comparison)
    let isAdditionalParent = false;
    if (family && !child && family.additionalParents && Array.isArray(family.additionalParents)) {
      for (const parent of family.additionalParents) {
        if (parent.phoneNumber) {
          const parentPhoneNormalized = normalizePhoneNumber(parent.phoneNumber);
          if (parentPhoneNormalized === normalizedPhone) {
            isAdditionalParent = true;
            console.log(`[VERIFY-OTP] ✅ User is an additional parent: ${parent.name}`);
            break;
          }
        }
      }
    }
    
    // Update lastLoginAt for the family
    if (db && family) {
      const now = new Date().toISOString();
      await db.collection('families').updateOne(
        { _id: family._id },
        { $set: { lastLoginAt: now } }
      );
      // Also update the family object in memory for immediate return
      family.lastLoginAt = now;
      invalidateFamilyCache(family._id);
    }
    
    // Remove OTP
    otpStore.delete(normalizedPhone);
    
    res.json({
      success: true,
      familyId: family._id,
      phoneNumber: normalizedPhone,
      isNewFamily: !storedOTP.familyId && !child && !isAdditionalParent,
      isChild: !!child,
      childId: child ? child._id : null,
      isAdditionalParent: isAdditionalParent
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
    const { name, phoneNumber } = req.body;
    
    console.log(`[CREATE-CHILD-ENDPOINT] Step 1: Validating input...`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Family ID: ${familyId}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Name: ${name || 'NOT PROVIDED'}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Phone: ${phoneNumber || 'NOT PROVIDED'}`);
    
    if (!name) {
      console.error(`[CREATE-CHILD-ENDPOINT] ❌ Name is required`);
      process.stderr.write(`[CREATE-CHILD-ENDPOINT] ❌ Name is required\n`);
      return res.status(400).json({ error: 'שם הילד נדרש' });
    }
    
    if (!phoneNumber) {
      console.error(`[CREATE-CHILD-ENDPOINT] ❌ Phone number is required`);
      process.stderr.write(`[CREATE-CHILD-ENDPOINT] ❌ Phone number is required\n`);
      return res.status(400).json({ error: 'מספר טלפון לילד נדרש' });
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
    const { child, phoneNumber: savedPhone } = await addChildToFamily(familyId, name.trim(), phoneNumber.trim());
    console.log(`[CREATE-CHILD-ENDPOINT] ✅ Child added successfully`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Child ID: ${child._id}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Child Name: ${child.name}`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Child Phone: ${savedPhone}`);
    
    const responseBody = {
      success: true,
      child: {
        _id: child._id,
        name: child.name,
        phoneNumber: child.phoneNumber,
        balance: child.balance,
        cashBoxBalance: child.cashBoxBalance,
        profileImage: child.profileImage,
        weeklyAllowance: child.weeklyAllowance,
        allowanceType: child.allowanceType,
        allowanceDay: child.allowanceDay,
        allowanceTime: child.allowanceTime,
        transactions: child.transactions
      },
      phoneNumber: savedPhone
    };
    
    const duration = Date.now() - requestStart;
    console.log(`[CREATE-CHILD-ENDPOINT] Step 4: Sending response...`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Response Status: 200`);
    console.log(`[CREATE-CHILD-ENDPOINT]   Response Body:`, JSON.stringify(responseBody, null, 2));
    console.log(`[CREATE-CHILD-ENDPOINT]   Duration: ${duration}ms`);
    console.log(`[CREATE-CHILD-ENDPOINT] ========================================\n`);
    
    process.stderr.write(`[CREATE-CHILD-ENDPOINT] ✅ Success - Child created: ${child._id}, Name: ${child.name}, Phone: ${savedPhone}\n`);
    
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

// Verify child password and return child
app.post('/api/auth/verify-child-password', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[VERIFY-CHILD-PASSWORD] ========================================`);
  console.log(`[VERIFY-CHILD-PASSWORD] 📥 Request received at ${timestamp}`);
  console.log(`[VERIFY-CHILD-PASSWORD] ========================================`);
  console.log(`[VERIFY-CHILD-PASSWORD] Family ID: ${req.body.familyId}`);
  console.log(`[VERIFY-CHILD-PASSWORD] Password: ${req.body.password ? '***' : 'NOT PROVIDED'}`);
  console.log(`[VERIFY-CHILD-PASSWORD] ========================================\n`);
  
  try {
    const { familyId, password } = req.body;
    
    if (!familyId || !password) {
      console.error(`[VERIFY-CHILD-PASSWORD] ❌ Missing familyId or password`);
      return res.status(400).json({ error: 'מספר משפחה וסיסמה נדרשים' });
    }
    
    console.log(`[VERIFY-CHILD-PASSWORD] Step 1: Getting family...`);
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[VERIFY-CHILD-PASSWORD] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    console.log(`[VERIFY-CHILD-PASSWORD] ✅ Family found: ${familyId}`);
    console.log(`[VERIFY-CHILD-PASSWORD]   Family has ${family.children?.length || 0} children`);
    
    if (!family.children || family.children.length === 0) {
      console.error(`[VERIFY-CHILD-PASSWORD] ❌ No children in family`);
      return res.status(400).json({ error: 'אין ילדים במשפחה זו' });
    }
    
    console.log(`[VERIFY-CHILD-PASSWORD] Step 2: Searching for child with matching password...`);
    const child = family.children.find(c => c.password === password.trim());
    
    if (!child) {
      console.error(`[VERIFY-CHILD-PASSWORD] ❌ No child found with matching password`);
      return res.status(401).json({ error: 'סיסמה שגויה' });
    }
    
    console.log(`[VERIFY-CHILD-PASSWORD] ✅ Child found: ${child._id} (${child.name})`);
    console.log(`[VERIFY-CHILD-PASSWORD] ========================================\n`);
    
    res.json({
      success: true,
      child: {
        _id: child._id,
        name: child.name,
        balance: child.balance || 0,
        cashBoxBalance: child.cashBoxBalance || 0,
        profileImage: child.profileImage || null,
        weeklyAllowance: child.weeklyAllowance || 0,
        allowanceType: child.allowanceType || 'weekly',
        allowanceDay: child.allowanceDay !== undefined ? child.allowanceDay : 1,
        allowanceTime: child.allowanceTime || '08:00',
        weeklyInterestRate: child.weeklyInterestRate || 0,
        lastAllowancePayment: child.lastAllowancePayment || null,
        totalInterestEarned: child.totalInterestEarned || 0,
        transactions: child.transactions || []
      }
    });
  } catch (error) {
    console.error(`[VERIFY-CHILD-PASSWORD] ========================================`);
    console.error(`[VERIFY-CHILD-PASSWORD] ❌❌❌ ERROR ❌❌❌`);
    console.error(`[VERIFY-CHILD-PASSWORD] ========================================`);
    console.error(`[VERIFY-CHILD-PASSWORD] Error Name: ${error.name || 'Unknown'}`);
    console.error(`[VERIFY-CHILD-PASSWORD] Error Message: ${error.message || 'No message'}`);
    console.error(`[VERIFY-CHILD-PASSWORD] Error Stack: ${error.stack || 'No stack'}`);
    console.error(`[VERIFY-CHILD-PASSWORD] ========================================\n`);
    
    res.status(500).json({ error: 'שגיאה באימות סיסמה' });
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
    // Optimize: Don't send all transactions in children list - they're fetched separately
    // This reduces payload size significantly when there are many transactions
    const children = (family.children || []).map(child => ({
      _id: child._id,
      name: child.name,
      phoneNumber: child.phoneNumber || '',
      balance: child.balance || 0,
      cashBoxBalance: child.cashBoxBalance || 0,
      profileImage: child.profileImage || null,
      weeklyAllowance: child.weeklyAllowance || 0,
      allowanceType: child.allowanceType || 'weekly',
      allowanceDay: child.allowanceDay !== undefined ? child.allowanceDay : 1,
      allowanceTime: child.allowanceTime || '08:00',
      weeklyInterestRate: child.weeklyInterestRate || 0,
      lastAllowancePayment: child.lastAllowancePayment || null,
      totalInterestEarned: child.totalInterestEarned || 0,
      // Don't include transactions here - they're fetched via separate endpoint
      // This reduces response size by 80-90% for families with many transactions
      transactionCount: (child.transactions || []).length
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
    
    // Calculate totalInterestEarned from ALL transactions to ensure accuracy
    // IMPORTANT: Only count transactions with id starting with "interest_" to prevent manipulation
    // Real interest transactions are created by the server with id format: "interest_${Date.now()}_${child._id}"
    let totalInterestEarned = child.totalInterestEarned || 0;
    const allTransactions = child.transactions || [];
    const interestTransactions = allTransactions.filter(t => 
      t && t.id && typeof t.id === 'string' && t.id.startsWith('interest_')
    );
    
    if (interestTransactions.length > 0) {
      const calculatedTotal = interestTransactions.reduce((sum, t) => sum + (t.amount || 0), 0);
      console.log(`[GET-CHILD] Found ${interestTransactions.length} interest transactions, calculated total: ${calculatedTotal.toFixed(2)}, stored: ${totalInterestEarned.toFixed(2)}`);
      console.log(`[GET-CHILD] Interest transactions:`, interestTransactions.map(t => ({ desc: t.description, amount: t.amount })));
      
      // Always use calculated value if we have interest transactions
      if (Math.abs(calculatedTotal - totalInterestEarned) > 0.01) { // Use small epsilon for float comparison
        totalInterestEarned = calculatedTotal;
        // Update the stored value in the database
        await db.collection('families').updateOne(
          { _id: familyId, 'children._id': childId },
          { $set: { 'children.$.totalInterestEarned': calculatedTotal } }
        );
        console.log(`[GET-CHILD] ✅ Updated totalInterestEarned to ${calculatedTotal.toFixed(2)} for child ${childId}`);
      }
    } else {
      console.log(`[GET-CHILD] No interest transactions found for child ${childId}. Total transactions: ${allTransactions.length}`);
    }
    
    res.json({
      name: child.name,
      phoneNumber: child.phoneNumber || '',
      balance: child.balance || 0,
      cashBoxBalance: child.cashBoxBalance || 0,
      profileImage: child.profileImage || null,
      weeklyAllowance: child.weeklyAllowance || 0,
      allowanceType: child.allowanceType || 'weekly',
      allowanceDay: child.allowanceDay !== undefined ? child.allowanceDay : 1,
      allowanceTime: child.allowanceTime || '08:00',
      weeklyInterestRate: child.weeklyInterestRate || 0,
      lastAllowancePayment: child.lastAllowancePayment || null,
      totalInterestEarned: totalInterestEarned,
      transactions: child.transactions || []
    });
  } catch (error) {
    console.error('Error fetching child:', error);
    res.status(500).json({ error: 'Failed to fetch child' });
  }
});

// Update child (name and phone number)
app.put('/api/families/:familyId/children/:childId', async (req, res) => {
  const requestStart = Date.now();
  const timestamp = new Date().toISOString();
  console.log(`\n[UPDATE-CHILD-SERVER] ========================================`);
  console.log(`[UPDATE-CHILD-SERVER] 📥 Request received at ${timestamp}`);
  console.log(`[UPDATE-CHILD-SERVER] Method: ${req.method}`);
  console.log(`[UPDATE-CHILD-SERVER] Path: ${req.path}`);
  console.log(`[UPDATE-CHILD-SERVER] Family ID: ${req.params.familyId}, Child ID: ${req.params.childId}`);
  console.log(`[UPDATE-CHILD-SERVER] Body:`, JSON.stringify(req.body, null, 2));
  console.log(`[UPDATE-CHILD-SERVER] ========================================\n`);
  process.stderr.write(`[UPDATE-CHILD-SERVER] Request received - Family: ${req.params.familyId}, Child: ${req.params.childId}\n`);
  
  try {
    const { familyId, childId } = req.params;
    const { name, phoneNumber } = req.body;
    
    console.log(`[UPDATE-CHILD-SERVER] Step 1: Validating input...`);
    if (!name || !phoneNumber) {
      console.error(`[UPDATE-CHILD-SERVER] ❌ Name and Phone Number are required`);
      process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Name and Phone Number are required\n`);
      return res.status(400).json({ error: 'שם ומספר טלפון נדרשים' });
    }
    console.log(`[UPDATE-CHILD-SERVER] ✅ Input validated: name="${name}", phoneNumber="${phoneNumber}"`);
    
    console.log(`[UPDATE-CHILD-SERVER] Step 2: Getting family...`);
    const family = await getFamilyById(familyId);
    if (!family) {
      console.error(`[UPDATE-CHILD-SERVER] ❌ Family not found: ${familyId}`);
      process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Family not found: ${familyId}\n`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    console.log(`[UPDATE-CHILD-SERVER] ✅ Family found: ${familyId}`);
    
    const childIndex = family.children?.findIndex(c => c._id === childId);
    if (childIndex === -1) {
      console.error(`[UPDATE-CHILD-SERVER] ❌ Child not found: ${childId} in family: ${familyId}`);
      process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Child not found: ${childId}\n`);
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    console.log(`[UPDATE-CHILD-SERVER] ✅ Child found at index: ${childIndex}`);
    
    const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
    const currentChild = family.children[childIndex];
    console.log(`[UPDATE-CHILD-SERVER] Current child phone: "${currentChild.phoneNumber}", New phone (raw): "${phoneNumber.trim()}", New phone (normalized): "${normalizedPhone}"`);
    
    // Check if phone number is already in use (as parent or child)
    // Compare normalized versions
    const currentNormalized = normalizePhoneNumber(currentChild.phoneNumber || '');
    if (currentNormalized !== normalizedPhone) {
      console.log(`[UPDATE-CHILD-SERVER] Step 3: Checking for duplicate phone number...`);
      
      // Check if phone number belongs to a parent (try both formats)
      if (db) {
        const existingFamilyByPhone = await getFamilyByPhone(normalizedPhone);
        if (existingFamilyByPhone) {
          console.error(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by a parent: ${normalizedPhone}`);
          process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by parent\n`);
          return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש על ידי הורה' });
        }
      }
      
      // Check if phone number belongs to another child in the same family (compare normalized)
      const existingChild = family.children.find(c => {
        if (c._id === childId) return false;
        const childNormalized = normalizePhoneNumber(c.phoneNumber || '');
        return childNormalized === normalizedPhone;
      });
      if (existingChild) {
        console.error(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by another child in same family: ${normalizedPhone}`);
        process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by child\n`);
        return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש על ידי ילד אחר' });
      }
      
      // Check if phone number belongs to a child in another family (normalize all children's phones for comparison)
      if (db) {
        const allFamilies = await db.collection('families').find({ _id: { $ne: familyId } }).toArray();
        for (const fam of allFamilies) {
          if (fam.children && Array.isArray(fam.children)) {
            for (const ch of fam.children) {
              if (ch.phoneNumber) {
                const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
                if (childPhoneNormalized === normalizedPhone) {
                  console.error(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by a child in another family: ${normalizedPhone} (found in family ${fam._id}, child ${ch._id})`);
                  process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Phone number already in use by child in another family\n`);
                  return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש על ידי ילד אחר' });
                }
              }
            }
          }
        }
      }
      
      console.log(`[UPDATE-CHILD-SERVER] ✅ Phone number not in use`);
    }
    
    console.log(`[UPDATE-CHILD-SERVER] Step 4: Updating child in database...`);
    const updateResult = await db.collection('families').updateOne(
      { _id: familyId, 'children._id': childId },
      { 
        $set: { 
          'children.$.name': name.trim(),
          'children.$.phoneNumber': normalizedPhone
        }
      }
    );
    console.log(`[UPDATE-CHILD-SERVER] Update result:`, JSON.stringify(updateResult, null, 2));
    
    if (updateResult.matchedCount === 0) {
      console.error(`[UPDATE-CHILD-SERVER] ❌ No document matched the update query`);
      process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ No document matched\n`);
      return res.status(404).json({ error: 'ילד לא נמצא במסד הנתונים' });
    }
    
    if (updateResult.modifiedCount === 0) {
      console.warn(`[UPDATE-CHILD-SERVER] ⚠️ Document matched but no changes were made`);
    } else {
      console.log(`[UPDATE-CHILD-SERVER] ✅ Child updated successfully`);
    }
    
    // Invalidate cache before fetching updated data
    invalidateFamilyCache(familyId);
    
    // Fetch updated child data to return in response
    console.log(`[UPDATE-CHILD-SERVER] Step 5: Fetching updated child data...`);
    const updatedFamily = await getFamilyById(familyId);
    const updatedChild = updatedFamily?.children?.find(c => c._id === childId);
    
    if (!updatedChild) {
      console.error(`[UPDATE-CHILD-SERVER] ❌ Updated child not found after update`);
      process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Updated child not found\n`);
      return res.status(500).json({ error: 'שגיאה בטעינת הנתונים המעודכנים' });
    }
    
    console.log(`[UPDATE-CHILD-SERVER] ✅ Updated child data:`, {
      _id: updatedChild._id,
      name: updatedChild.name,
      phoneNumber: updatedChild.phoneNumber
    });
    
    const responseBody = { 
      success: true, 
      message: 'ילד עודכן בהצלחה',
      child: {
        _id: updatedChild._id,
        name: updatedChild.name,
        phoneNumber: updatedChild.phoneNumber
      }
    };
    const duration = Date.now() - requestStart;
    console.log(`[UPDATE-CHILD-SERVER] Step 6: Sending response...`);
    console.log(`[UPDATE-CHILD-SERVER]   Response Status: 200`);
    console.log(`[UPDATE-CHILD-SERVER]   Response Body:`, JSON.stringify(responseBody, null, 2));
    console.log(`[UPDATE-CHILD-SERVER]   Duration: ${duration}ms`);
    console.log(`[UPDATE-CHILD-SERVER] ========================================\n`);
    process.stderr.write(`[UPDATE-CHILD-SERVER] ✅ Success - Child updated: ${childId}, Name: ${name.trim()}, Phone: ${normalizedPhone}\n`);
    
    res.json(responseBody);
  } catch (error) {
    const duration = Date.now() - requestStart;
    console.error(`[UPDATE-CHILD-SERVER] ========================================`);
    console.error(`[UPDATE-CHILD-SERVER] ❌❌❌ ERROR ❌❌❌`);
    console.error(`[UPDATE-CHILD-SERVER] Error Name:`, error.name);
    console.error(`[UPDATE-CHILD-SERVER] Error Message:`, error.message);
    console.error(`[UPDATE-CHILD-SERVER] Error Stack:`, error.stack);
    console.error(`[UPDATE-CHILD-SERVER] Full Error:`, error);
    console.error(`[UPDATE-CHILD-SERVER] Duration: ${duration}ms`);
    console.error(`[UPDATE-CHILD-SERVER] ========================================\n`);
    process.stderr.write(`[UPDATE-CHILD-SERVER] ❌ Error: ${error.message}\n`);
    res.status(500).json({ error: error.message || 'שגיאה בעדכון ילד' });
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
    const transactions = child.transactions || [];
    
    // Optimize sorting: pre-sort only if needed, use efficient date comparison
    // Sort in descending order (newest first) - optimized for performance
    let sortedTransactions = transactions;
    if (transactions.length > 0) {
      // Use efficient sorting - compare timestamps directly (faster than Date objects)
      sortedTransactions = transactions.slice().sort((a, b) => {
        // If dates are ISO strings, compare directly (faster)
        if (a.date && b.date) {
          return b.date.localeCompare(a.date);
        }
        // Fallback to Date objects if needed
        return new Date(b.date || 0) - new Date(a.date || 0);
      });
    }
    
    // Apply limit after sorting (more efficient than sorting all then limiting)
    if (limit && limit > 0) {
      sortedTransactions = sortedTransactions.slice(0, limit);
    }
    
    res.json({ transactions: sortedTransactions });
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
    
    // Calculate balance increment/decrement instead of recalculating all
    const balanceChange = type === 'deposit' ? parseFloat(amount) : -parseFloat(amount);
    const newBalance = (child.balance || 0) + balanceChange;
    
    if (db) {
      // Use $push to add transaction and $inc to update balance atomically
      // This is much faster than loading all transactions and recalculating
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $push: { 'children.$.transactions': transaction },
          $inc: { 'children.$.balance': balanceChange }
        }
      );
      // Invalidate cache to ensure fresh data on next request
      invalidateFamilyCache(familyId);
    }
    
    res.json({ transaction, balance: newBalance, updated: true });
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
      // Invalidate cache
      invalidateFamilyCache(familyId);
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
      invalidateFamilyCache(familyId);
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
      invalidateFamilyCache(familyId);
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
      invalidateFamilyCache(familyId);
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
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true, profileImage: profileImage || null });
  } catch (error) {
    console.error('Error updating profile image:', error);
    res.status(500).json({ error: 'Failed to update profile image' });
  }
});

// Update parent profile image
app.put('/api/families/:familyId/parent/profile-image', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { profileImage } = req.body;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { parentProfileImage: profileImage || null } }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true, profileImage: profileImage || null });
  } catch (error) {
    console.error('Error updating parent profile image:', error);
    res.status(500).json({ error: 'Failed to update parent profile image' });
  }
});

// Update weekly allowance
// Savings Goal endpoints
app.get('/api/families/:familyId/children/:childId/savings-goal', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const family = await db.collection('families').findOne({ _id: familyId });
    
    if (!family) {
      return res.status(404).json({ error: 'Family not found' });
    }
    
    const child = family.children?.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    res.json({ savingsGoal: child.savingsGoal || null });
  } catch (error) {
    console.error('Error getting savings goal:', error);
    res.status(500).json({ error: 'Failed to get savings goal' });
  }
});

app.put('/api/families/:familyId/children/:childId/savings-goal', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const { name, targetAmount } = req.body;
    
    if (!name || !targetAmount || targetAmount <= 0) {
      return res.status(400).json({ error: 'Name and targetAmount (positive number) are required' });
    }
    
    const family = await db.collection('families').findOne({ _id: familyId });
    if (!family) {
      return res.status(404).json({ error: 'Family not found' });
    }
    
    const childIndex = family.children?.findIndex(c => c._id === childId);
    if (childIndex === -1) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    const savingsGoal = {
      name: name.trim(),
      targetAmount: parseFloat(targetAmount),
      createdAt: family.children[childIndex].savingsGoal?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    await db.collection('families').updateOne(
      { _id: familyId, 'children._id': childId },
      { $set: { 'children.$.savingsGoal': savingsGoal } }
    );
    invalidateFamilyCache(familyId);
    
    res.json({ success: true, savingsGoal });
  } catch (error) {
    console.error('Error updating savings goal:', error);
    res.status(500).json({ error: 'Failed to update savings goal' });
  }
});

app.delete('/api/families/:familyId/children/:childId/savings-goal', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    
    await db.collection('families').updateOne(
      { _id: familyId, 'children._id': childId },
      { $unset: { 'children.$.savingsGoal': '' } }
    );
    invalidateFamilyCache(familyId);
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting savings goal:', error);
    res.status(500).json({ error: 'Failed to delete savings goal' });
  }
});

app.put('/api/families/:familyId/children/:childId/weekly-allowance', async (req, res) => {
  try {
    const { familyId, childId } = req.params;
    const { weeklyAllowance, allowanceType, allowanceDay, allowanceTime, weeklyInterestRate } = req.body;
    
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
    
    // Validate interest rate if provided
    let interestRate = undefined;
    if (weeklyInterestRate !== undefined && weeklyInterestRate !== null && weeklyInterestRate !== '') {
      interestRate = parseFloat(weeklyInterestRate);
      if (isNaN(interestRate) || interestRate < 0 || interestRate > 100) {
        return res.status(400).json({ error: 'Weekly interest rate must be a valid number between 0 and 100' });
      }
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const updateFields = {
      'children.$.weeklyAllowance': amount,
      'children.$.allowanceType': type,
      'children.$.allowanceDay': day,
      'children.$.allowanceTime': time
    };
    
    if (interestRate !== undefined) {
      updateFields['children.$.weeklyInterestRate'] = interestRate;
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $set: updateFields
        }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ 
      success: true, 
      weeklyAllowance: amount, 
      allowanceType: type, 
      allowanceDay: day, 
      allowanceTime: time,
      weeklyInterestRate: interestRate
    });
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
    
    // Calculate balance increment instead of recalculating all
    const balanceChange = child.weeklyAllowance;
    const newBalance = (child.balance || 0) + balanceChange;
    
    if (db) {
      // Use atomic operations for better performance
      await db.collection('families').updateOne(
        { _id: familyId, 'children._id': childId },
        { 
          $push: { 'children.$.transactions': transaction },
          $inc: { 'children.$.balance': balanceChange }
        }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true, transaction, balance: newBalance });
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

// ========== TASKS API ENDPOINTS ==========

// Get all tasks for a family
app.get('/api/families/:familyId/tasks', async (req, res) => {
  try {
    const { familyId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    res.json({ tasks: family.tasks || [] });
  } catch (error) {
    console.error('Error fetching tasks:', error);
    res.status(500).json({ error: 'Failed to fetch tasks' });
  }
});

// Create a new task
app.post('/api/families/:familyId/tasks', async (req, res) => {
  try {
    console.log('[ADD-TASK] Request received:', {
      familyId: req.params.familyId,
      body: req.body,
      method: req.method,
      url: req.url
    });
    
    const { familyId } = req.params;
    const { name, price, activeFor } = req.body;
    
    if (!name || price === undefined) {
      console.log('[ADD-TASK] Validation failed: missing name or price');
      return res.status(400).json({ error: 'Task name and price are required' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      console.log('[ADD-TASK] Family not found:', familyId);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const task = {
      _id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: name.trim(),
      price: parseFloat(price),
      activeFor: activeFor || [],
      createdAt: new Date().toISOString()
    };
    
    if (!family.tasks) {
      family.tasks = [];
    }
    family.tasks.push(task);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { tasks: family.tasks } }
      );
      invalidateFamilyCache(familyId);
    }
    
    console.log('[ADD-TASK] Task added successfully:', task._id);
    res.json({ task });
  } catch (error) {
    console.error('[ADD-TASK] Error adding task:', error);
    console.error('[ADD-TASK] Error stack:', error.stack);
    res.status(500).json({ error: 'Failed to add task', details: error.message });
  }
});

// Update a task
app.put('/api/families/:familyId/tasks/:taskId', async (req, res) => {
  try {
    const { familyId, taskId } = req.params;
    const { name, price, activeFor } = req.body;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const task = family.tasks?.find(t => t._id === taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    if (name !== undefined) task.name = name.trim();
    if (price !== undefined) task.price = parseFloat(price);
    if (activeFor !== undefined) task.activeFor = activeFor;
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { tasks: family.tasks } }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error updating task:', error);
    res.status(500).json({ error: 'Failed to update task' });
  }
});

// Delete a task
app.delete('/api/families/:familyId/tasks/:taskId', async (req, res) => {
  try {
    const { familyId, taskId } = req.params;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    if (!family.tasks) {
      family.tasks = [];
    }
    family.tasks = family.tasks.filter(t => t._id !== taskId);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { tasks: family.tasks } }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting task:', error);
    res.status(500).json({ error: 'Failed to delete task' });
  }
});

// Request payment for a task
app.post('/api/families/:familyId/tasks/:taskId/request-payment', async (req, res) => {
  try {
    const { familyId, taskId } = req.params;
    const { childId, note, image } = req.body;
    
    if (!childId) {
      return res.status(400).json({ error: 'Child ID is required' });
    }
    
    // Validate image size if provided (max 500KB base64)
    if (image && image.length > 500 * 1024) {
      console.warn(`[REQUEST-PAYMENT] Image too large: ${(image.length / 1024).toFixed(2)} KB`);
      return res.status(400).json({ error: 'תמונה גדולה מדי. אנא בחר תמונה קטנה יותר.' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const task = family.tasks?.find(t => t._id === taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    const child = family.children?.find(c => c._id === childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    if (!task.activeFor.includes(childId)) {
      return res.status(400).json({ error: 'Task is not active for this child' });
    }
    
    const paymentRequest = {
      _id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      taskId,
      taskName: task.name,
      taskPrice: task.price,
      childId,
      childName: child.name,
      note: note || null,
      image: image || null, // Image should already be compressed by client
      status: 'pending', // 'pending', 'approved', 'rejected'
      requestedAt: new Date().toISOString(),
      completedAt: null
    };
    
    if (!family.paymentRequests) {
      family.paymentRequests = [];
    }
    family.paymentRequests.push(paymentRequest);
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { paymentRequests: family.paymentRequests } }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ paymentRequest });
  } catch (error) {
    console.error('Error creating payment request:', error);
    res.status(500).json({ error: 'Failed to create payment request' });
  }
});

// Get pending payment requests
app.get('/api/families/:familyId/payment-requests', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { status } = req.query; // Optional: filter by status
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    let requests = family.paymentRequests || [];
    if (status) {
      requests = requests.filter(r => r.status === status);
    }
    
    res.json({ paymentRequests: requests });
  } catch (error) {
    console.error('Error fetching payment requests:', error);
    res.status(500).json({ error: 'Failed to fetch payment requests' });
  }
});

// Approve payment request
app.put('/api/families/:familyId/payment-requests/:requestId/approve', async (req, res) => {
  try {
    const { familyId, requestId } = req.params;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const request = family.paymentRequests?.find(r => r._id === requestId);
    if (!request) {
      return res.status(404).json({ error: 'Payment request not found' });
    }
    
    if (request.status !== 'pending') {
      const statusMessage = request.status === 'approved' 
        ? 'הבקשה כבר אושרה' 
        : request.status === 'rejected' 
        ? 'הבקשה כבר נדחתה'
        : `הבקשה במצב: ${request.status}`;
      return res.status(400).json({ error: statusMessage });
    }
    
    const child = family.children?.find(c => c._id === request.childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    // Update request status
    request.status = 'approved';
    request.completedAt = new Date().toISOString();
    
    // Add transaction to child
    const transaction = {
      id: `task_${Date.now()}_${request.childId}`,
      type: 'deposit',
      amount: request.taskPrice,
      description: `תשלום על משימה: ${request.taskName}`,
      date: new Date().toISOString(),
      category: 'משימות בית'
    };
    
    if (!child.transactions) {
      child.transactions = [];
    }
    child.transactions.push(transaction);
    
    // Update child balance
    child.balance = (child.balance || 0) + request.taskPrice;
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { 
          $set: { 
            paymentRequests: family.paymentRequests,
            children: family.children
          }
        }
      );
      
      // Invalidate cache if functions exist
      try {
        if (typeof invalidateFamilyCache === 'function') {
          invalidateFamilyCache(familyId);
        }
        if (typeof invalidateChildCache === 'function') {
          invalidateChildCache(familyId, request.childId);
        }
      } catch (cacheError) {
        console.warn('Cache invalidation error (non-critical):', cacheError);
      }
    }
    
    res.json({ success: true, transaction });
  } catch (error) {
    console.error('Error approving payment request:', error);
    res.status(500).json({ error: 'Failed to approve payment request: ' + (error.message || 'Unknown error') });
  }
});

// Reject payment request
app.put('/api/families/:familyId/payment-requests/:requestId/reject', async (req, res) => {
  try {
    const { familyId, requestId } = req.params;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const request = family.paymentRequests?.find(r => r._id === requestId);
    if (!request) {
      return res.status(404).json({ error: 'Payment request not found' });
    }
    
    if (request.status !== 'pending') {
      return res.status(400).json({ error: 'Request is not pending' });
    }
    
    // Update request status
    request.status = 'rejected';
    request.completedAt = new Date().toISOString();
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { paymentRequests: family.paymentRequests } }
      );
      invalidateFamilyCache(familyId);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error rejecting payment request:', error);
    res.status(500).json({ error: 'Failed to reject payment request' });
  }
});

// Get task history (all payment requests with status approved or rejected)
app.get('/api/families/:familyId/tasks/history', async (req, res) => {
  try {
    const { familyId } = req.params;
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const requests = (family.paymentRequests || []).filter(r => 
      r.status === 'approved' || r.status === 'rejected'
    );
    
    res.json({ history: requests });
  } catch (error) {
    console.error('Error fetching task history:', error);
    res.status(500).json({ error: 'Failed to fetch task history' });
  }
});

// Update payment request status (for history screen)
app.put('/api/families/:familyId/payment-requests/:requestId/status', async (req, res) => {
  try {
    const { familyId, requestId } = req.params;
    const { status } = req.body; // 'approved' or 'rejected'
    
    if (!['approved', 'rejected'].includes(status)) {
      return res.status(400).json({ error: 'Invalid status' });
    }
    
    const family = await getFamilyById(familyId);
    if (!family) {
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const request = family.paymentRequests?.find(r => r._id === requestId);
    if (!request) {
      return res.status(404).json({ error: 'Payment request not found' });
    }
    
    const oldStatus = request.status;
    request.status = status;
    request.completedAt = new Date().toISOString();
    
    const child = family.children?.find(c => c._id === request.childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    // If changing from rejected to approved, add money
    if (oldStatus === 'rejected' && status === 'approved') {
      const transaction = {
        id: `task_${Date.now()}_${request.childId}`,
        type: 'deposit',
        amount: request.taskPrice,
        description: `תשלום על משימה: ${request.taskName}`,
        date: new Date().toISOString(),
        category: 'משימות בית'
      };
      
      if (!child.transactions) {
        child.transactions = [];
      }
      child.transactions.push(transaction);
      child.balance = (child.balance || 0) + request.taskPrice;
    }
    
    // If changing from approved to rejected, remove money
    if (oldStatus === 'approved' && status === 'rejected') {
      // Find and remove the transaction
      if (child.transactions) {
        child.transactions = child.transactions.filter(t => 
          !(t.description && t.description.includes(`תשלום על משימה: ${request.taskName}`) && 
            Math.abs(t.amount - request.taskPrice) < 0.01)
        );
      }
      child.balance = Math.max(0, (child.balance || 0) - request.taskPrice);
    }
    
    if (db) {
      await db.collection('families').updateOne(
        { _id: familyId },
        { 
          $set: { 
            paymentRequests: family.paymentRequests,
            children: family.children
          }
        }
      );
      invalidateFamilyCache(familyId);
      invalidateChildCache(familyId, request.childId);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error updating payment request status:', error);
    res.status(500).json({ error: 'Failed to update payment request status' });
  }
});

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
// Get family info (for parents management)
app.get('/api/families/:familyId', async (req, res) => {
  try {
    const { familyId } = req.params;
    
    // Use projection to exclude transactions and other large fields
    const family = await db.collection('families').findOne(
      { _id: familyId },
      {
        projection: {
          _id: 1,
          phoneNumber: 1,
          parentName: 1,
          parentProfileImage: 1,
          additionalParents: 1,
          createdAt: 1,
          lastLoginAt: 1,
          // Exclude large fields
          'children.transactions': 0,
          'children.profileImage': 0
        }
      }
    );
    
    if (!family) {
      return res.status(404).json({ error: 'Family not found' });
    }
    
    // Get parents list (phoneNumber is the main parent, and any additional parents)
    const parents = [];
    if (family.phoneNumber) {
      parents.push({
        phoneNumber: family.phoneNumber,
        name: family.parentName || 'הורה1',
        isMain: true
      });
    }
    
    // Add any additional parents if they exist
    if (family.additionalParents && Array.isArray(family.additionalParents)) {
      family.additionalParents.forEach(parent => {
        parents.push({
          phoneNumber: parent.phoneNumber,
          name: parent.name || 'הורה נוסף',
          isMain: false
        });
      });
    }
    
    res.json({
      _id: family._id,
      phoneNumber: family.phoneNumber,
      parentName: family.parentName || 'הורה1',
      parentProfileImage: family.parentProfileImage || null,
      parents: parents,
      createdAt: family.createdAt,
      lastLoginAt: family.lastLoginAt
    });
  } catch (error) {
    console.error('Error getting family info:', error);
    res.status(500).json({ error: 'Failed to get family info' });
  }
});

// Add a new parent to the family
app.post('/api/families/:familyId/parent', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[ADD-PARENT] ========================================`);
  console.log(`[ADD-PARENT] ➕ ADD PARENT REQUEST`);
  console.log(`[ADD-PARENT] ========================================`);
  console.log(`[ADD-PARENT] Timestamp: ${timestamp}`);
  console.log(`[ADD-PARENT] Family ID: ${req.params.familyId}`);
  console.log(`[ADD-PARENT] Body: ${JSON.stringify(req.body)}`);
  console.log(`[ADD-PARENT] ========================================\n`);

  try {
    if (!db) {
      console.error(`[ADD-PARENT] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }

    const { familyId } = req.params;
    const { name, phoneNumber } = req.body;

    if (!name || !phoneNumber) {
      console.log(`[ADD-PARENT] ❌ Missing name or phoneNumber`);
      return res.status(400).json({ error: 'שם ומספר טלפון נדרשים' });
    }

    const family = await db.collection('families').findOne({ _id: familyId });
    if (!family) {
      console.log(`[ADD-PARENT] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }

    const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
    console.log(`[ADD-PARENT] Normalized phone: ${normalizedPhone}`);
    
    // Check if phone is already in use by the main parent (normalize both for comparison)
    const mainParentPhoneNormalized = normalizePhoneNumber(family.phoneNumber);
    if (mainParentPhoneNormalized === normalizedPhone) {
      console.log(`[ADD-PARENT] ❌ Phone already in use by main parent: ${normalizedPhone}`);
      return res.status(400).json({ error: 'מספר טלפון זה כבר שייך להורה הראשי' });
    }

    // Check if phone is already in use by another additional parent (normalize all for comparison)
    const additionalParents = family.additionalParents || [];
    for (const parent of additionalParents) {
      if (parent.phoneNumber) {
        const parentPhoneNormalized = normalizePhoneNumber(parent.phoneNumber);
        if (parentPhoneNormalized === normalizedPhone) {
          console.log(`[ADD-PARENT] ❌ Phone already in use by additional parent: ${normalizedPhone}`);
          return res.status(400).json({ error: 'מספר טלפון זה כבר קיים במשפחה' });
        }
      }
    }

    // Check if phone is already in use by another family (as main parent or additional parent)
    // getFamilyByPhone already normalizes and checks both main and additional parents
    const existingFamily = await getFamilyByPhone(normalizedPhone);
    if (existingFamily && existingFamily._id !== familyId) {
      console.log(`[ADD-PARENT] ❌ Phone already in use by another family: ${normalizedPhone} (family: ${existingFamily._id})`);
      return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש במשפחה אחרת' });
    }
    
    // Also check if phone is already in use by a child in any family (normalize all for comparison)
    const allFamilies = await db.collection('families').find({}).toArray();
    for (const fam of allFamilies) {
      if (fam.children && Array.isArray(fam.children)) {
        for (const ch of fam.children) {
          if (ch.phoneNumber) {
            const childPhoneNormalized = normalizePhoneNumber(ch.phoneNumber);
            if (childPhoneNormalized === normalizedPhone) {
              console.log(`[ADD-PARENT] ❌ Phone already in use by a child: ${normalizedPhone} (family: ${fam._id}, child: ${ch._id})`);
              return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש על ידי ילד' });
            }
          }
        }
      }
    }

    // Add the new parent to additionalParents array
    const newParent = {
      phoneNumber: normalizedPhone,
      name: name.trim(),
      isMain: false
    };

    await db.collection('families').updateOne(
      { _id: familyId },
      { 
        $push: { additionalParents: newParent }
      }
    );

    console.log(`[ADD-PARENT] ✅ Parent added successfully to family ${familyId}`);
    res.json({ 
      success: true, 
      message: 'הורה נוסף בהצלחה',
      parent: newParent
    });
  } catch (error) {
    console.error('[ADD-PARENT] Error adding parent:', error);
    res.status(500).json({ error: 'שגיאה בהוספת הורה', details: error.message });
  }
});

// Update parent info (name or phone)
app.put('/api/families/:familyId/parent', async (req, res) => {
  try {
    const { familyId } = req.params;
    const { name, phoneNumber, isMain } = req.body;
    
    const family = await db.collection('families').findOne({ _id: familyId });
    if (!family) {
      return res.status(404).json({ error: 'Family not found' });
    }
    
    if (isMain) {
      // Update main parent
      const updateData = {};
      if (name !== undefined) {
        updateData.parentName = name.trim();
      }
      if (phoneNumber !== undefined) {
        const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
        // Check if phone is already in use by another family
        const existingFamily = await getFamilyByPhone(normalizedPhone);
        if (existingFamily && existingFamily._id !== familyId) {
          return res.status(400).json({ error: 'מספר טלפון זה כבר בשימוש במשפחה אחרת' });
        }
        updateData.phoneNumber = normalizedPhone;
      }
      
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: updateData }
      );
      invalidateFamilyCache(familyId);
    } else {
      // Update additional parent
      const { parentIndex } = req.body;
      if (parentIndex !== undefined && family.additionalParents && family.additionalParents[parentIndex]) {
        const updateData = {};
        if (name !== undefined) {
          family.additionalParents[parentIndex].name = name.trim();
          updateData[`additionalParents.${parentIndex}.name`] = name.trim();
        }
        if (phoneNumber !== undefined) {
          const normalizedPhone = normalizePhoneNumber(phoneNumber.trim());
          family.additionalParents[parentIndex].phoneNumber = normalizedPhone;
          updateData[`additionalParents.${parentIndex}.phoneNumber`] = normalizedPhone;
        }
        
        if (Object.keys(updateData).length > 0) {
          await db.collection('families').updateOne(
            { _id: familyId },
            { $set: updateData }
          );
          invalidateFamilyCache(familyId);
        }
      }
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error updating parent info:', error);
    res.status(500).json({ error: 'Failed to update parent info' });
  }
});

// Archive a parent - move to archive collection instead of deleting
app.post('/api/families/:familyId/parent/archive', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[ARCHIVE-PARENT] ========================================`);
  console.log(`[ARCHIVE-PARENT] 📦 ARCHIVE PARENT REQUEST`);
  console.log(`[ARCHIVE-PARENT] ========================================`);
  console.log(`[ARCHIVE-PARENT] Timestamp: ${timestamp}`);
  console.log(`[ARCHIVE-PARENT] Family ID: ${req.params.familyId}`);
  console.log(`[ARCHIVE-PARENT] Body: ${JSON.stringify(req.body)}`);
  console.log(`[ARCHIVE-PARENT] ========================================\n`);
  
  try {
    if (!db) {
      console.error(`[ARCHIVE-PARENT] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    const { familyId } = req.params;
    const { parentIndex, isMain } = req.body;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[ARCHIVE-PARENT] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    let parent = null;
    if (isMain) {
      // Archive main parent
      parent = {
        phoneNumber: family.phoneNumber,
        name: family.parentName || 'הורה1',
        isMain: true
      };
      
      // Cannot archive main parent - return error
      return res.status(400).json({ error: 'לא ניתן למחוק את ההורה הראשי' });
    } else {
      // Archive additional parent
      // Validate parentIndex
      if (parentIndex === undefined || parentIndex === null) {
        console.error(`[ARCHIVE-PARENT] ❌ parentIndex is required for additional parent`);
        console.error(`[ARCHIVE-PARENT] Received parentIndex: ${parentIndex}, isMain: ${isMain}`);
        return res.status(400).json({ error: 'parentIndex נדרש למחיקת הורה נוסף' });
      }
      
      if (!family.additionalParents || !Array.isArray(family.additionalParents)) {
        console.error(`[ARCHIVE-PARENT] ❌ No additional parents array found`);
        console.error(`[ARCHIVE-PARENT] Family has additionalParents: ${!!family.additionalParents}, type: ${typeof family.additionalParents}`);
        return res.status(404).json({ error: 'אין הורים נוספים במשפחה' });
      }
      
      if (parentIndex < 0 || parentIndex >= family.additionalParents.length) {
        console.error(`[ARCHIVE-PARENT] ❌ Parent index out of range`);
        console.error(`[ARCHIVE-PARENT] Requested index: ${parentIndex}, Available parents: ${family.additionalParents.length}`);
        console.error(`[ARCHIVE-PARENT] Available parent indices: 0-${family.additionalParents.length - 1}`);
        return res.status(404).json({ error: `הורה לא נמצא באינדקס ${parentIndex}. יש ${family.additionalParents.length} הורים נוספים (אינדקסים 0-${family.additionalParents.length - 1})` });
      }
      
      parent = family.additionalParents[parentIndex];
      console.log(`[ARCHIVE-PARENT] ✅ Found parent at index ${parentIndex}: ${parent.name || 'no name'}`);
    }
    
    console.log(`[ARCHIVE-PARENT] Archiving parent: ${parent.name || 'no name'}`);
    
    // Create archived parent document with all data
    const archivedParent = {
      ...parent,
      archivedAt: new Date().toISOString(),
      archivedFromFamily: familyId,
      familyPhoneNumber: family.phoneNumber
    };
    
    // Save to archive collection
    await db.collection('archived_parents').insertOne(archivedParent);
    console.log(`[ARCHIVE-PARENT] ✅ Parent saved to archive`);
    
    // Remove parent from family
    if (isMain) {
      // Should not happen, but handle it
      return res.status(400).json({ error: 'לא ניתן למחוק את ההורה הראשי' });
    } else {
      family.additionalParents = family.additionalParents.filter((_, idx) => idx !== parentIndex);
      
      // Update family in database
      await db.collection('families').updateOne(
        { _id: familyId },
        { $set: { additionalParents: family.additionalParents } }
      );
    }
    
    // Invalidate cache
    invalidateFamilyCache(familyId);
    
    console.log(`[ARCHIVE-PARENT] ✅ Parent archived successfully`);
    res.json({
      success: true,
      message: 'הורה הועבר לארכיון בהצלחה'
    });
  } catch (error) {
    console.error(`[ARCHIVE-PARENT] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה בהעברת ההורה לארכיון',
      details: error.message 
    });
  }
});

// Admin endpoint - Get all users
app.get('/api/admin/all-users', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[GET-ALL-USERS] ========================================`);
  console.log(`[GET-ALL-USERS] 📊 GET ALL USERS REQUEST`);
  console.log(`[GET-ALL-USERS] ========================================`);
  console.log(`[GET-ALL-USERS] Timestamp: ${timestamp}`);
  console.log(`[GET-ALL-USERS] Method: ${req.method}`);
  console.log(`[GET-ALL-USERS] Path: ${req.path}`);
  console.log(`[GET-ALL-USERS] ========================================\n`);
  
  try {
    if (!db) {
      console.error(`[GET-ALL-USERS] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    console.log(`[GET-ALL-USERS] Fetching all families...`);
    const families = await db.collection('families').find({}).toArray();
    console.log(`[GET-ALL-USERS] ✅ Found ${families.length} families`);
    
    // Format the response
    const formattedFamilies = families.map(family => ({
      _id: family._id,
      phoneNumber: family.phoneNumber || 'לא זמין',
      createdAt: family.createdAt || null,
      lastLoginAt: family.lastLoginAt || null,
      children: family.children || {}
    }));
    
    console.log(`[GET-ALL-USERS] ✅ Returning ${formattedFamilies.length} families`);
    res.json({ 
      success: true,
      families: formattedFamilies,
      totalFamilies: formattedFamilies.length
    });
  } catch (error) {
    console.error(`[GET-ALL-USERS] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה בטעינת המשתמשים',
      details: error.message 
    });
  }
});

// Admin endpoint - Delete a single family
app.delete('/api/admin/families/:familyId', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[DELETE-FAMILY] ========================================`);
  console.log(`[DELETE-FAMILY] ⚠️ DELETE FAMILY REQUEST`);
  console.log(`[DELETE-FAMILY] ========================================`);
  console.log(`[DELETE-FAMILY] Timestamp: ${timestamp}`);
  console.log(`[DELETE-FAMILY] Method: ${req.method}`);
  console.log(`[DELETE-FAMILY] Path: ${req.path}`);
  console.log(`[DELETE-FAMILY] Original URL: ${req.originalUrl}`);
  console.log(`[DELETE-FAMILY] Family ID: ${req.params.familyId}`);
  console.log(`[DELETE-FAMILY] ========================================\n`);
  
  process.stderr.write(`[DELETE-FAMILY] ⚠️ DELETE FAMILY REQUEST - ${req.params.familyId}\n`);
  
  try {
    if (!db) {
      console.error(`[DELETE-FAMILY] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    const { familyId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[DELETE-FAMILY] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    console.log(`[DELETE-FAMILY] Deleting family: ${familyId} (${family.phoneNumber || 'no phone'})`);
    const deleteResult = await db.collection('families').deleteOne({ _id: familyId });
    
    if (deleteResult.deletedCount === 0) {
      console.error(`[DELETE-FAMILY] ❌ Failed to delete family`);
      return res.status(500).json({ error: 'שגיאה במחיקת המשפחה' });
    }
    
    console.log(`[DELETE-FAMILY] ✅ Family deleted successfully`);
    res.json({
      success: true,
      message: 'משפחה נמחקה בהצלחה',
      deletedCount: deleteResult.deletedCount
    });
  } catch (error) {
    console.error(`[DELETE-FAMILY] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה במחיקת המשפחה',
      details: error.message 
    });
  }
});

// Admin endpoint - Delete a single child
app.delete('/api/admin/families/:familyId/children/:childId', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[DELETE-CHILD] ========================================`);
  console.log(`[DELETE-CHILD] ⚠️ DELETE CHILD REQUEST`);
  console.log(`[DELETE-CHILD] ========================================`);
  console.log(`[DELETE-CHILD] Timestamp: ${timestamp}`);
  console.log(`[DELETE-CHILD] Family ID: ${req.params.familyId}`);
  console.log(`[DELETE-CHILD] Child ID: ${req.params.childId}`);
  console.log(`[DELETE-CHILD] ========================================\n`);
  
  try {
    if (!db) {
      console.error(`[DELETE-CHILD] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    const { familyId, childId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[DELETE-CHILD] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children?.find(c => c._id === childId);
    if (!child) {
      console.error(`[DELETE-CHILD] ❌ Child not found: ${childId}`);
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    console.log(`[DELETE-CHILD] Deleting child: ${childId} (${child.name || 'no name'})`);
    
    // Remove child from family
    family.children = family.children.filter(c => c._id !== childId);
    
    // Remove child from all categories' activeFor arrays
    if (family.categories) {
      family.categories.forEach(category => {
        if (category.activeFor) {
          category.activeFor = category.activeFor.filter(id => id !== childId);
        }
      });
    }
    
    await db.collection('families').updateOne(
      { _id: familyId },
      { 
        $set: { 
          children: family.children,
          categories: family.categories
        }
      }
    );
    
    console.log(`[DELETE-CHILD] ✅ Child deleted successfully`);
    res.json({
      success: true,
      message: 'ילד נמחק בהצלחה'
    });
  } catch (error) {
    console.error(`[DELETE-CHILD] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה במחיקת הילד',
      details: error.message 
    });
  }
});

// Archive a child - move to archive collection instead of deleting
app.post('/api/families/:familyId/children/:childId/archive', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[ARCHIVE-CHILD] ========================================`);
  console.log(`[ARCHIVE-CHILD] 📦 ARCHIVE CHILD REQUEST`);
  console.log(`[ARCHIVE-CHILD] ========================================`);
  console.log(`[ARCHIVE-CHILD] Timestamp: ${timestamp}`);
  console.log(`[ARCHIVE-CHILD] Family ID: ${req.params.familyId}`);
  console.log(`[ARCHIVE-CHILD] Child ID: ${req.params.childId}`);
  console.log(`[ARCHIVE-CHILD] ========================================\n`);
  
  try {
    if (!db) {
      console.error(`[ARCHIVE-CHILD] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    const { familyId, childId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[ARCHIVE-CHILD] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    const child = family.children?.find(c => c._id === childId);
    if (!child) {
      console.error(`[ARCHIVE-CHILD] ❌ Child not found: ${childId}`);
      return res.status(404).json({ error: 'ילד לא נמצא' });
    }
    
    console.log(`[ARCHIVE-CHILD] Archiving child: ${childId} (${child.name || 'no name'})`);
    
    // Create archived child document with all data
    const archivedChild = {
      ...child,
      archivedAt: new Date().toISOString(),
      archivedFromFamily: familyId,
      familyPhoneNumber: family.phoneNumber
    };
    
    // Save to archive collection
    await db.collection('archived_children').insertOne(archivedChild);
    console.log(`[ARCHIVE-CHILD] ✅ Child saved to archive`);
    
    // Remove child from family
    family.children = family.children.filter(c => c._id !== childId);
    
    // Remove child from all categories' activeFor arrays
    if (family.categories) {
      family.categories.forEach(category => {
        if (category.activeFor) {
          category.activeFor = category.activeFor.filter(id => id !== childId);
        }
      });
    }
    
    // Update family in database
    await db.collection('families').updateOne(
      { _id: familyId },
      { 
        $set: { 
          children: family.children,
          categories: family.categories
        }
      }
    );
    
    // Invalidate cache
    invalidateFamilyCache(familyId);
    
    console.log(`[ARCHIVE-CHILD] ✅ Child archived successfully`);
    res.json({
      success: true,
      message: 'ילד הועבר לארכיון בהצלחה'
    });
  } catch (error) {
    console.error(`[ARCHIVE-CHILD] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה בהעברת הילד לארכיון',
      details: error.message 
    });
  }
});

// Archive entire family - move to archive collection and release phone numbers
app.post('/api/families/:familyId/archive', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[ARCHIVE-FAMILY] ========================================`);
  console.log(`[ARCHIVE-FAMILY] 📦 ARCHIVE FAMILY REQUEST`);
  console.log(`[ARCHIVE-FAMILY] ========================================`);
  console.log(`[ARCHIVE-FAMILY] Timestamp: ${timestamp}`);
  console.log(`[ARCHIVE-FAMILY] Family ID: ${req.params.familyId}`);
  console.log(`[ARCHIVE-FAMILY] ========================================\n`);
  
  try {
    if (!db) {
      console.error(`[ARCHIVE-FAMILY] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    const { familyId } = req.params;
    const family = await getFamilyById(familyId);
    
    if (!family) {
      console.error(`[ARCHIVE-FAMILY] ❌ Family not found: ${familyId}`);
      return res.status(404).json({ error: 'משפחה לא נמצאה' });
    }
    
    console.log(`[ARCHIVE-FAMILY] Archiving family: ${familyId} (${family.phoneNumber || 'no phone'})`);
    
    // Create archived family document with all data
    const archivedFamily = {
      ...family,
      archivedAt: new Date().toISOString(),
      archivedFamilyId: familyId
    };
    
    // Save to archive collection
    await db.collection('archived_families').insertOne(archivedFamily);
    console.log(`[ARCHIVE-FAMILY] ✅ Family saved to archive`);
    
    // Archive all children separately (for easier querying)
    if (family.children && Array.isArray(family.children)) {
      for (const child of family.children) {
        const archivedChild = {
          ...child,
          archivedAt: new Date().toISOString(),
          archivedFromFamily: familyId,
          familyPhoneNumber: family.phoneNumber
        };
        await db.collection('archived_children').insertOne(archivedChild);
      }
      console.log(`[ARCHIVE-FAMILY] ✅ Archived ${family.children.length} children`);
    }
    
    // Archive all parents separately
    if (family.additionalParents && Array.isArray(family.additionalParents)) {
      for (const parent of family.additionalParents) {
        const archivedParent = {
          ...parent,
          archivedAt: new Date().toISOString(),
          archivedFromFamily: familyId,
          familyPhoneNumber: family.phoneNumber
        };
        await db.collection('archived_parents').insertOne(archivedParent);
      }
      console.log(`[ARCHIVE-FAMILY] ✅ Archived ${family.additionalParents.length} additional parents`);
    }
    
    // Archive main parent
    if (family.phoneNumber) {
      const archivedMainParent = {
        phoneNumber: family.phoneNumber,
        name: family.parentName || 'הורה ראשי',
        archivedAt: new Date().toISOString(),
        archivedFromFamily: familyId,
        familyPhoneNumber: family.phoneNumber
      };
      await db.collection('archived_parents').insertOne(archivedMainParent);
      console.log(`[ARCHIVE-FAMILY] ✅ Archived main parent`);
    }
    
    // Delete family from main collection (this releases phone numbers)
    await db.collection('families').deleteOne({ _id: familyId });
    console.log(`[ARCHIVE-FAMILY] ✅ Family deleted from main collection`);
    
    // Delete OTP codes for this family
    await db.collection('otpCodes').deleteMany({ familyId });
    console.log(`[ARCHIVE-FAMILY] ✅ OTP codes deleted`);
    
    // Invalidate cache
    invalidateFamilyCache(familyId);
    
    console.log(`[ARCHIVE-FAMILY] ✅ Family archived successfully`);
    console.log(`[ARCHIVE-FAMILY] Phone numbers released for reuse`);
    
    res.json({
      success: true,
      message: 'הפרופיל המשפחתי נמחק והועבר לארכיון בהצלחה'
    });
  } catch (error) {
    console.error(`[ARCHIVE-FAMILY] ❌ Error:`, error);
    res.status(500).json({ 
      error: 'שגיאה בהעברת הפרופיל המשפחתי לארכיון',
      details: error.message 
    });
  }
});

// Admin endpoint - Delete all users and data
app.delete('/api/admin/delete-all-users', async (req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`\n[DELETE-ALL-USERS] ========================================`);
  console.log(`[DELETE-ALL-USERS] ⚠️⚠️⚠️ DELETE ALL USERS REQUEST ⚠️⚠️⚠️`);
  console.log(`[DELETE-ALL-USERS] ========================================`);
  console.log(`[DELETE-ALL-USERS] Timestamp: ${timestamp}`);
  console.log(`[DELETE-ALL-USERS] Method: ${req.method}`);
  console.log(`[DELETE-ALL-USERS] Path: ${req.path}`);
  console.log(`[DELETE-ALL-USERS] ========================================\n`);
  
  process.stderr.write(`[DELETE-ALL-USERS] ⚠️⚠️⚠️ DELETE ALL USERS REQUEST ⚠️⚠️⚠️\n`);
  
  try {
    if (!db) {
      console.error(`[DELETE-ALL-USERS] ❌ No database connection`);
      return res.status(500).json({ error: 'אין חיבור למסד הנתונים' });
    }
    
    console.log(`[DELETE-ALL-USERS] Step 1: Counting families...`);
    const countBefore = await db.collection('families').countDocuments();
    console.log(`[DELETE-ALL-USERS]   Families before deletion: ${countBefore}`);
    
    if (countBefore === 0) {
      console.log(`[DELETE-ALL-USERS] ⚠️  No families to delete`);
      return res.json({ 
        success: true, 
        message: 'אין משתמשים במערכת',
        deletedCount: 0 
      });
    }
    
    console.log(`[DELETE-ALL-USERS] Step 2: Deleting all families...`);
    const deleteResult = await db.collection('families').deleteMany({});
    console.log(`[DELETE-ALL-USERS] ✅ Deletion completed`);
    console.log(`[DELETE-ALL-USERS]   Deleted count: ${deleteResult.deletedCount}`);
    
    // Also clear in-memory stores
    console.log(`[DELETE-ALL-USERS] Step 3: Clearing in-memory stores...`);
    otpStore.clear();
    childCodesStore.clear();
    console.log(`[DELETE-ALL-USERS] ✅ In-memory stores cleared`);
    
    console.log(`[DELETE-ALL-USERS] ========================================`);
    console.log(`[DELETE-ALL-USERS] ✅✅✅ ALL USERS DELETED ✅✅✅`);
    console.log(`[DELETE-ALL-USERS] ========================================`);
    console.log(`[DELETE-ALL-USERS] Deleted families: ${deleteResult.deletedCount}`);
    console.log(`[DELETE-ALL-USERS] ========================================\n`);
    
    process.stderr.write(`[DELETE-ALL-USERS] ✅ Deleted ${deleteResult.deletedCount} families\n`);
    
    res.json({
      success: true,
      message: 'כל המשתמשים והנתונים נמחקו בהצלחה',
      deletedCount: deleteResult.deletedCount
    });
  } catch (error) {
    console.error(`[DELETE-ALL-USERS] ========================================`);
    console.error(`[DELETE-ALL-USERS] ❌❌❌ ERROR ❌❌❌`);
    console.error(`[DELETE-ALL-USERS] ========================================`);
    console.error(`[DELETE-ALL-USERS] Error Name: ${error.name || 'Unknown'}`);
    console.error(`[DELETE-ALL-USERS] Error Message: ${error.message || 'No message'}`);
    console.error(`[DELETE-ALL-USERS] Error Stack: ${error.stack || 'No stack'}`);
    console.error(`[DELETE-ALL-USERS] ========================================\n`);
    
    process.stderr.write(`[DELETE-ALL-USERS] ❌ ERROR: ${error.message}\n`);
    
    res.status(500).json({ 
      error: 'שגיאה במחיקת המשתמשים',
      details: error.message 
    });
  }
});

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


