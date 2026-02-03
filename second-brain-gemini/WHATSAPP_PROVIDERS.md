# WhatsApp Providers Integration

This document describes the WhatsApp provider architecture and how to use it.

## Architecture

The application now supports multiple WhatsApp providers through a unified interface:

1. **WhatsAppProvider** - Abstract base class defining the interface
2. **WhatsAppProviderFactory** - Factory pattern for creating provider instances
3. **TwilioService** - Implements WhatsAppProvider for Twilio
4. **MetaWhatsAppService** - Implements WhatsAppProvider for Meta WhatsApp Cloud API

## Configuration

### Provider Selection

Set `WHATSAPP_PROVIDER` in your environment variables:
- `twilio` - Use Twilio (default)
- `meta` - Use Meta WhatsApp Cloud API

### Environment Variables

See `ENV_VARIABLES.md` for complete list of required variables.

## Usage

### Getting a Provider Instance

```python
from app.services.whatsapp_provider import WhatsAppProviderFactory

# Get provider based on WHATSAPP_PROVIDER setting
provider = WhatsAppProviderFactory.create_provider()

# Or specify a provider explicitly
provider = WhatsAppProviderFactory.create_provider('meta')
```

### Sending Messages

```python
if provider:
    result = provider.send_whatsapp(
        message="Hello from Second Brain!",
        to="+972XXXXXXXXX"  # Required for Meta, optional for Twilio
    )
    
    if result.get('success'):
        print("Message sent successfully!")
    else:
        print(f"Error: {result.get('error')}")
```

## Provider-Specific Notes

### Twilio
- Uses `TWILIO_WHATSAPP_TO` as default recipient if `to` parameter is not provided
- Supports both WhatsApp and SMS
- Phone numbers should include `whatsapp:` prefix

### Meta WhatsApp Cloud API
- Requires `to` parameter (no default recipient)
- Phone numbers should be in E.164 format (e.g., `+972XXXXXXXXX`)
- Supports webhook verification via `verify_webhook()` method

## Switching Providers

To switch providers, simply change the `WHATSAPP_PROVIDER` environment variable:

```bash
# Use Twilio
WHATSAPP_PROVIDER=twilio

# Use Meta
WHATSAPP_PROVIDER=meta
```

No code changes required!
