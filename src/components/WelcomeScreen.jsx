import React from 'react';

const WelcomeScreen = ({ onSelectCreate, onSelectJoin }) => {
  const handleTestLogs = async () => {
    try {
      // Use the same logic as api.js
      const PRODUCTION_API = 'https://kids-money-manager-production.up.railway.app/api';
      let apiUrl;
      
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        apiUrl = PRODUCTION_API;
      } else if (import.meta.env.VITE_API_URL) {
        apiUrl = import.meta.env.VITE_API_URL;
      } else if (import.meta.env.DEV) {
        apiUrl = 'http://localhost:3001/api';
      } else {
        apiUrl = PRODUCTION_API;
      }
      
      console.log('[TEST-LOGS] Sending request to:', `${apiUrl}/test-logs`);
      
      const response = await fetch(`${apiUrl}/test-logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('[TEST-LOGS] Success:', data);
        alert('✅ לוג נשלח בהצלחה! בדוק את ה-Logs ב-Railway.');
      } else {
        console.error('[TEST-LOGS] Error response:', response.status, response.statusText);
        alert(`❌ שגיאה בשליחת הלוג: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('[TEST-LOGS] Error:', error);
      alert(`❌ שגיאה בשליחת הלוג: ${error.message}`);
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
        <span className="version">גרסה 2.9.18</span>
      </footer>
    </div>
  );
};

export default WelcomeScreen;
