import React from 'react';

const WelcomeScreen = ({ onSelectCreate, onSelectJoin }) => {
  return (
    <div className="welcome-screen">
      <div className="welcome-container">
        <div className="welcome-header">
          <h1>👨‍👩‍👧‍👦 Kids Money Manager</h1>
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
    </div>
  );
};

export default WelcomeScreen;

