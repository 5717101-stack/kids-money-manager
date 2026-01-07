import React from 'react';

const WelcomeScreen = ({ onSelectCreate, onSelectJoin }) => {
  const handleTestLogs = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-production.up.railway.app/api';
      await fetch(`${apiUrl}/test-logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      console.error('Error sending test log:', error);
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
