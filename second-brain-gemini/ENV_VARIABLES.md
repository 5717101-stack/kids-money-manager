# Environment Variables Configuration

This document describes all environment variables needed for the Second Brain application.

## Required Variables

### Google Gemini API
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

## WhatsApp Provider Configuration

### Provider Selection
```bash
# Options: 'twilio' or 'meta'
# Default: 'twilio'
WHATSAPP_PROVIDER=twilio
```

### Twilio Configuration (for WhatsApp/SMS)
```bash
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+972XXXXXXXXX
TWILIO_SMS_FROM=+14155238886
TWILIO_SMS_TO=+972XXXXXXXXX
```

### Meta WhatsApp Cloud API Configuration
```bash
WHATSAPP_CLOUD_API_TOKEN=your_meta_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_meta_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verification_token
WHATSAPP_FROM=+972XXXXXXXXX  # Sender phone number (E.164 format, optional - Phone Number ID is used by default)
WHATSAPP_TO=+972XXXXXXXXX  # Recipient phone number (E.164 format, required for Meta)

# Optional: For automatic token refresh (recommended to prevent daily errors)
WHATSAPP_APP_ID=your_meta_app_id
WHATSAPP_APP_SECRET=your_meta_app_secret
```

**Important Notes:**
- Access tokens expire after 60 days (or sooner for short-lived tokens)
- To enable automatic token refresh, set both `WHATSAPP_APP_ID` and `WHATSAPP_APP_SECRET`
- Without these, you'll need to manually update `WHATSAPP_CLOUD_API_TOKEN` when it expires
- To get a long-lived token (60 days), use Meta's Graph API Explorer or exchange a short-lived token

## Server Settings
```bash
PORT=8000
DEBUG=false
ENABLE_SMS=false  # Set to 'true' to enable SMS sending (default: false)
```

## Notes

- Set `WHATSAPP_PROVIDER` to switch between 'twilio' and 'meta'
- Both providers can be configured simultaneously, but only the selected provider will be used
- The default provider is 'twilio' for backward compatibility
