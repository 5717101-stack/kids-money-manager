"""
Twilio WhatsApp Webhook Handler
Flask application for handling incoming WhatsApp messages via Twilio.
"""

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

# Initialize Flask app
app = Flask(__name__)

# Initialize Google Gemini AI model
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Initialize the model
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini model initialized successfully")
else:
    model = None
    print("⚠️  GEMINI_API_KEY not found - Gemini model not initialized")


@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Handle incoming WhatsApp messages from Twilio.
    Extracts sender number and message body, logs to console,
    and returns a TwiML response.
    """
    try:
        # Extract sender's number and message body from Twilio request
        sender_number = request.form.get('From', '')
        message_body = request.form.get('Body', '')
        
        # Print incoming message to console logs
        print(f"\n{'='*50}")
        print(f"📱 Incoming WhatsApp Message")
        print(f"{'='*50}")
        print(f"From: {sender_number}")
        print(f"Message: {message_body}")
        print(f"{'='*50}\n")
        
        # Create TwiML response
        response = MessagingResponse()
        response.message('Message received and saved to memory.')
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        print(f"❌ Error processing WhatsApp message: {str(e)}")
        # Return error response
        response = MessagingResponse()
        response.message('Sorry, an error occurred while processing your message.')
        return str(response), 500, {'Content-Type': 'text/xml'}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for deployment monitoring."""
    return {'status': 'healthy', 'service': 'twilio-whatsapp-webhook'}, 200


if __name__ == '__main__':
    # Get port from environment variables, default to 5000
    port = int(os.getenv('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
