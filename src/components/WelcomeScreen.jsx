import React from 'react';

const WelcomeScreen = ({ onSelectCreate, onSelectJoin }) => {
  const handleTestLogs = async () => {
    console.log('========================================');
    console.log('[TEST-LOGS] 🎯 Button clicked!');
    console.log('[TEST-LOGS] Starting test logs request...');
    console.log('========================================');
    
    try {
      // Use the same logic as api.js
      const PRODUCTION_API = 'https://kids-money-manager-production.up.railway.app/api';
      let apiUrl;
      
      console.log('[TEST-LOGS] Checking environment...');
      console.log('[TEST-LOGS] window.Capacitor:', typeof window !== 'undefined' ? window.Capacitor : 'N/A');
      console.log('[TEST-LOGS] import.meta.env.VITE_API_URL:', import.meta.env.VITE_API_URL);
      console.log('[TEST-LOGS] import.meta.env.DEV:', import.meta.env.DEV);
      
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        apiUrl = PRODUCTION_API;
        console.log('[TEST-LOGS] Using mobile app - PRODUCTION_API');
      } else if (import.meta.env.VITE_API_URL) {
        apiUrl = import.meta.env.VITE_API_URL;
        console.log('[TEST-LOGS] Using VITE_API_URL from env');
      } else if (import.meta.env.DEV) {
        apiUrl = 'http://localhost:3001/api';
        console.log('[TEST-LOGS] Using development - localhost');
      } else {
        apiUrl = PRODUCTION_API;
        console.log('[TEST-LOGS] Using fallback - PRODUCTION_API');
      }
      
      const fullUrl = `${apiUrl}/test-logs`;
      console.log('[TEST-LOGS] ========================================');
      console.log('[TEST-LOGS] Full URL:', fullUrl);
      console.log('[TEST-LOGS] Sending POST request...');
      console.log('[TEST-LOGS] ========================================');
      
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ test: true })
      });
      
      console.log('[TEST-LOGS] Response received!');
      console.log('[TEST-LOGS] Status:', response.status);
      console.log('[TEST-LOGS] Status Text:', response.statusText);
      console.log('[TEST-LOGS] Headers:', Object.fromEntries(response.headers.entries()));
      
      if (response.ok) {
        const data = await response.json();
        console.log('[TEST-LOGS] ========================================');
        console.log('[TEST-LOGS] ✅ SUCCESS!');
        console.log('[TEST-LOGS] Response data:', data);
        console.log('[TEST-LOGS] ========================================');
        alert('✅ לוג נשלח בהצלחה! בדוק את ה-Logs ב-Railway.');
      } else {
        const errorText = await response.text();
        console.error('[TEST-LOGS] ========================================');
        console.error('[TEST-LOGS] ❌ ERROR RESPONSE');
        console.error('[TEST-LOGS] Status:', response.status);
        console.error('[TEST-LOGS] Status Text:', response.statusText);
        console.error('[TEST-LOGS] Error body:', errorText);
        console.error('[TEST-LOGS] ========================================');
        alert(`❌ שגיאה בשליחת הלוג: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('[TEST-LOGS] ========================================');
      console.error('[TEST-LOGS] ❌ EXCEPTION CAUGHT');
      console.error('[TEST-LOGS] Error name:', error.name);
      console.error('[TEST-LOGS] Error message:', error.message);
      console.error('[TEST-LOGS] Error stack:', error.stack);
      console.error('[TEST-LOGS] Full error:', error);
      console.error('[TEST-LOGS] ========================================');
      alert(`❌ שגיאה בשליחת הלוג: ${error.message}\n\nפתח את ה-Console (F12) כדי לראות פרטים נוספים.`);
    }
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-container">
        <div className="welcome-header">
          <h1>👨‍👩‍👧‍👦 <span className="kids-red">Kids</span> Money Manager</h1>
          <p className="welcome-subtitle">ניהול כספי לילדים</p>
        </div>
        
        <div className="welcome-options">
          <button 
            className="welcome-button create-button"
            onClick={onSelectCreate}
          >
            <span className="button-icon">➕</span>
            <span className="button-text">
              <strong>הקמת חשבון משפחתי חדש</strong>
              <small>צור חשבון חדש למשפחה שלך</small>
            </span>
          </button>
          
          <button 
            className="welcome-button join-button"
            onClick={onSelectJoin}
          >
            <span className="button-icon">🔗</span>
            <span className="button-text">
              <strong>הצטרפות לחשבון משפחתי קיים</strong>
              <small>הצטרף למשפחה קיימת עם קוד</small>
            </span>
          </button>
        </div>
      </div>
      <footer className="app-footer">
        <button 
          className="test-logs-button"
          onClick={handleTestLogs}
          title="בדיקת לוגים"
        >
          🔍 בדיקת לוגים
        </button>
        <span className="version">גרסה 2.9.19</span>
      </footer>
    </div>
  );
};

export default WelcomeScreen;
