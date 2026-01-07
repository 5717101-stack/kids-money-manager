import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const JoinChildScreen = ({ onVerified, onBack }) => {
  const { t } = useTranslation();
  const [childCode, setChildCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const code = childCode.trim();
      
      if (!code) {
        setError('אנא הכנס קוד גישה');
        setLoading(false);
        return;
      }

      console.log('[JOIN-CHILD] Attempting to join with code:', code.substring(0, 2) + '***');
      
      // The joinCode is 6 characters and identifies both family and child
      // We need an endpoint that can search by this code
      // For now, let's try a search endpoint or use admin endpoint to find the child
      
      // Try endpoint: /children/search-by-code or /families/search-child
      let response;
      let data;
      
      try {
        // Try search endpoint
        response = await fetch(`${apiUrl}/children/search-by-code`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ joinCode: code.toUpperCase() })
        });
        
        if (response.ok) {
          const responseText = await response.text();
          if (responseText.trim().startsWith('<!DOCTYPE') || responseText.trim().startsWith('<html')) {
            throw new Error('השרת החזיר שגיאה');
          }
          data = JSON.parse(responseText);
        } else {
          throw new Error('Endpoint not found');
        }
      } catch (firstError) {
        console.log('[JOIN-CHILD] First endpoint failed, trying alternative...');
        
        // Alternative: Try /families/search-child-by-code
        try {
          response = await fetch(`${apiUrl}/families/search-child-by-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code.toUpperCase() })
          });
          
          if (response.ok) {
            const responseText = await response.text();
            if (responseText.trim().startsWith('<!DOCTYPE') || responseText.trim().startsWith('<html')) {
              throw new Error('השרת החזיר שגיאה');
            }
            data = JSON.parse(responseText);
          } else {
            throw new Error('Endpoint not found');
          }
        } catch (secondError) {
          console.error('[JOIN-CHILD] Both endpoints failed');
          // Show helpful message - this feature requires backend support
          setError('תכונה זו דורשת תמיכה בשרת. אנא פנה להורה לקבלת קוד גישה או השתמש בסיסמת הילד דרך "הצטרפות לחשבון משפחתי קיים".');
          setLoading(false);
          return;
        }
      }

      if (data && data.familyId && data.childId) {
        console.log('[JOIN-CHILD] ✅ Successfully found child:', data.childId);
        sessionStorage.setItem('familyId', data.familyId);
        sessionStorage.setItem('childId', data.childId);
        sessionStorage.setItem('isChildView', 'true');
        onVerified(data.familyId, data.childId, data.child || { _id: data.childId });
      } else {
        setError(data?.error || 'קוד גישה לא נמצא');
      }
    } catch (err) {
      console.error('[JOIN-CHILD] Error:', err);
      
      // Better error handling
      let errorMessage = err.message || t('auth.invalidCode');
      
      if (err.message.includes('404') || err.message.includes('Not Found')) {
        errorMessage = 'קוד גישה לא נמצא. אנא ודא שהקוד נכון או פנה להורה.';
      } else if (err.message.includes('JSON') || err.message.includes('DOCTYPE')) {
        errorMessage = 'שגיאת שרת. אנא נסה שוב מאוחר יותר.';
      } else if (err.message.includes('השרת החזיר שגיאה')) {
        errorMessage = 'השרת החזיר שגיאה. אנא נסה שוב מאוחר יותר.';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="join-child-screen" style={{ padding: '20px', maxWidth: '400px', margin: '0 auto' }}>
      <h1>{t('welcome.joinAsChild')}</h1>
      <p>{t('welcome.joinAsChildDesc')}</p>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '16px' }}>
          <label>{t('auth.enterChildCode')}</label>
          <input
            type="text"
            value={childCode}
            onChange={(e) => setChildCode(e.target.value)}
            placeholder="Enter child access code"
            required
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '16px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              marginTop: '8px'
            }}
          />
        </div>

        {error && (
          <div style={{ color: '#ef4444', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              flex: 1,
              padding: '12px',
              backgroundColor: 'var(--bg-secondary)',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            {t('common.back')}
          </button>
          <button
            type="submit"
            disabled={loading}
            style={{
              flex: 1,
              padding: '12px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? t('common.loading') : t('auth.verify')}
          </button>
        </div>
      </form>
    </div>
  );
};

export default JoinChildScreen;
