import { PushNotifications } from '@capacitor/push-notifications';
import { apiCall } from '../utils/api';

class PushNotificationService {
  constructor() {
    this.isRegistered = false;
    this.deviceToken = null;
    this.familyId = null;
  }

  async initialize(familyId) {
    this.familyId = familyId;
    
    // Request permission
    let permStatus = await PushNotifications.checkPermissions();
    
    if (permStatus.receive === 'prompt') {
      permStatus = await PushNotifications.requestPermissions();
    }
    
    if (permStatus.receive !== 'granted') {
      console.log('Push notification permission denied');
      return false;
    }

    // Register for push notifications
    await PushNotifications.register();

    // Set up event listeners
    this.setupListeners();

    return true;
  }

  setupListeners() {
    // Registration event
    PushNotifications.addListener('registration', async (token) => {
      console.log('Push registration success, token: ' + token.value);
      this.deviceToken = token.value;
      this.isRegistered = true;
      
      // Send token to server
      if (this.familyId) {
        await this.registerToken(token.value);
      }
    });

    // Registration error event
    PushNotifications.addListener('registrationError', (error) => {
      console.error('Error on registration: ' + JSON.stringify(error));
    });

    // Push notification received event
    PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.log('Push notification received: ', notification);
      // Notification is shown automatically by the system
    });

    // Push notification action performed event
    PushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
      console.log('Push notification action performed', notification.actionId, notification.inputValue);
    });
  }

  async registerToken(token) {
    try {
      if (!this.familyId) {
        console.warn('Cannot register token: familyId not set');
        return;
      }

      await apiCall(`/api/families/${this.familyId}/push-token`, {
        method: 'POST',
        body: JSON.stringify({ token, platform: this.getPlatform() })
      });
      
      console.log('Push token registered successfully');
    } catch (error) {
      console.error('Error registering push token:', error);
    }
  }

  getPlatform() {
    // Detect platform - this will be set by Capacitor
    if (window.Capacitor?.getPlatform() === 'ios') {
      return 'ios';
    } else if (window.Capacitor?.getPlatform() === 'android') {
      return 'android';
    }
    return 'web';
  }

  async unregister() {
    try {
      if (this.familyId && this.deviceToken) {
        await apiCall(`/api/families/${this.familyId}/push-token`, {
          method: 'DELETE',
          body: JSON.stringify({ token: this.deviceToken })
        });
      }
      this.deviceToken = null;
      this.isRegistered = false;
    } catch (error) {
      console.error('Error unregistering push token:', error);
    }
  }
}

// Export singleton instance
export const pushNotificationService = new PushNotificationService();
