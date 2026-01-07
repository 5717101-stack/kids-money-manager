import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getParentInviteCode } from '../utils/api';

const JoinParentScreen = ({ onVerified, onBack }) => {
  const { t } = useTranslation();
  const [inviteCode, setInviteCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // TODO: Implement API call to verify parent invite code
      // For now, simulate verification
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api'}/families/join-parent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inviteCode })
      });

      if (response.ok) {
        const data = await response.json();
        sessionStorage.setItem('familyId', data.familyId);
        sessionStorage.setItem('parentLoggedIn', 'true');
        onVerified(data.familyId);
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
    <div className="join-parent-screen" style={{ padding: '20px', maxWidth: '400px', margin: '0 auto' }}>
      <h1>{t('welcome.joinAsParent')}</h1>
      <p>{t('welcome.joinAsParentDesc')}</p>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '16px' }}>
          <label>{t('auth.enterInviteCode')}</label>
          <input
            type="text"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            placeholder="Enter invite code"
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

export default JoinParentScreen;
