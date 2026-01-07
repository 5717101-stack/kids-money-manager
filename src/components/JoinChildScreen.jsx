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
      const response = await fetch(`${apiUrl}/families/join-child`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ childCode })
      });

      if (response.ok) {
        const data = await response.json();
        sessionStorage.setItem('familyId', data.familyId);
        sessionStorage.setItem('childId', data.childId);
        sessionStorage.setItem('isChildView', 'true');
        onVerified(data.familyId, data.childId, data.child);
      } else {
        const errorData = await response.json();
        setError(errorData.error || t('auth.invalidCode'));
      }
    } catch (err) {
      setError(err.message || t('auth.invalidCode'));
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
