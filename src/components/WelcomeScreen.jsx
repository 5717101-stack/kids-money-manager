import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import UsersTable from './UsersTable';

const WelcomeScreen = ({ onSelectCreate, onSelectJoinAsParent, onSelectJoinAsChild }) => {
  const { t } = useTranslation();
  const [showUsersTable, setShowUsersTable] = useState(false);
  const handleDeleteAllUsers = async () => {
    // First confirmation
    const firstConfirm = window.confirm(
      '⚠️ אזהרה: פעולה זו תמחק את כל המשתמשים והנתונים מהמערכת!\n\n' +
      'זה כולל:\n' +
      '• כל המשפחות\n' +
      '• כל הילדים\n' +
      '• כל העסקאות\n' +
      '• כל הקטגוריות\n' +
      '• כל התמונות\n\n' +
      'האם אתה בטוח שברצונך להמשיך?'
    );
    
    if (!firstConfirm) {
      return;
    }
    
    // Second confirmation with typing requirement
    const confirmText = 'מחק הכל';
    const userInput = window.prompt(
      '⚠️⚠️⚠️ פעולה מסוכנת מאוד! ⚠️⚠️⚠️\n\n' +
      'זה ימחק את כל הנתונים ללא אפשרות שחזור!\n\n' +
      'אם אתה בטוח, הקלד "' + confirmText + '" כדי לאשר:'
    );
    
    if (userInput !== confirmText) {
      alert('הפעולה בוטלה. לא הקלדת את הטקסט הנכון.');
      return;
    }
    
    // Final confirmation
    const finalConfirm = window.confirm(
      '⚠️⚠️⚠️ אישור אחרון! ⚠️⚠️⚠️\n\n' +
      'אתה עומד למחוק את כל הנתונים מהמערכת.\n\n' +
      'זה לא ניתן לביטול!\n\n' +
      'לחץ OK רק אם אתה בטוח לחלוטין.'
    );
    
    if (!finalConfirm) {
      return;
    }
    
    try {
      console.log('[DELETE-ALL] Starting delete all users...');
      
      // Use the same logic as api.js
      const PRODUCTION_API = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      let apiUrl;
      
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        apiUrl = PRODUCTION_API;
        console.log('[DELETE-ALL] Using mobile app - PRODUCTION_API');
      } else if (import.meta.env.VITE_API_URL) {
        apiUrl = import.meta.env.VITE_API_URL;
        console.log('[DELETE-ALL] Using VITE_API_URL from env');
      } else if (import.meta.env.DEV) {
        apiUrl = 'http://localhost:3001/api';
        console.log('[DELETE-ALL] Using development - localhost');
      } else {
        apiUrl = PRODUCTION_API;
        console.log('[DELETE-ALL] Using fallback - PRODUCTION_API');
      }
      
      const fullUrl = `${apiUrl}/admin/delete-all-users`;
      console.log('[DELETE-ALL] Full URL:', fullUrl);
      
      const response = await fetch(fullUrl, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        console.log('[DELETE-ALL] ✅ Success:', data);
        alert(`✅ כל המשתמשים והנתונים נמחקו בהצלחה!\n\nנמחקו ${data.deletedCount || 0} משפחות.`);
        // Reload page to reset state
        window.location.reload();
      } else {
        console.error('[DELETE-ALL] ❌ Error:', data);
        alert(`❌ שגיאה במחיקה: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('[DELETE-ALL] ❌ Exception:', error);
      alert(`❌ שגיאה במחיקה: ${error.message}`);
    }
  };

  const handleTestLogs = async () => {
    console.log('========================================');
    console.log('[TEST-LOGS] 🎯 Button clicked!');
    console.log('[TEST-LOGS] Starting test logs request...');
    console.log('========================================');
    
    try {
      // Use the same logic as api.js
      const PRODUCTION_API = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
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
          <h1 dangerouslySetInnerHTML={{ __html: t('welcome.title') }} />
          <p className="welcome-subtitle">{t('welcome.subtitle')}</p>
        </div>
        
        <div className="welcome-options">
          <button 
            className="welcome-button create-button"
            onClick={onSelectCreate}
          >
            <span className="button-icon">➕</span>
            <span className="button-text">
              <strong>{t('welcome.createFamily')}</strong>
              <small>{t('welcome.createFamilyDesc')}</small>
            </span>
          </button>
          
          <button 
            className="welcome-button join-button"
            onClick={onSelectJoinAsParent}
          >
            <span className="button-icon">👨‍👩‍👧‍👦</span>
            <span className="button-text">
              <strong>{t('welcome.joinAsParent')}</strong>
              <small>{t('welcome.joinAsParentDesc')}</small>
            </span>
          </button>

          <button 
            className="welcome-button join-button"
            onClick={onSelectJoinAsChild}
            style={{ backgroundColor: '#ec4899' }}
          >
            <span className="button-icon">👦</span>
            <span className="button-text">
              <strong>{t('welcome.joinAsChild')}</strong>
              <small>{t('welcome.joinAsChildDesc')}</small>
            </span>
          </button>
        </div>
      </div>
      <footer className="app-footer">
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button 
            className="users-table-button"
            onClick={() => setShowUsersTable(true)}
            title="הצג טבלת משתמשים"
            style={{
              padding: '8px 16px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            📊 טבלת משתמשים
          </button>
          <button 
            className="delete-all-button"
            onClick={handleDeleteAllUsers}
            title="מחק את כל המשתמשים והנתונים"
            style={{
              padding: '8px 16px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            🗑️ מחק הכל
          </button>
        </div>
        <span className="version">{t('common.version')} 3.4.39</span>
      </footer>
      
      {showUsersTable && (
        <UsersTable onClose={() => setShowUsersTable(false)} />
      )}
    </div>
  );
};

export default WelcomeScreen;
