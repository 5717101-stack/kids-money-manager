import React, { useState } from 'react';

const ChildJoin = ({ familyId, onJoined, onCancel }) => {
  const [joinCode, setJoinCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!joinCode || joinCode.length !== 6) {
      setError('קוד הצטרפות חייב להיות 6 תווים');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3001/api'}/families/${familyId}/children/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          joinCode: joinCode.toUpperCase()
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'קוד הצטרפות שגוי');
      }

      onJoined(data.child);
    } catch (error) {
      console.error('Error joining child:', error);
      setError(error.message || 'קוד הצטרפות שגוי או פג תוקף');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="child-join-overlay">
      <div className="child-join-container">
        <div className="child-join-header">
          <h2>הצטרפות לחשבון משפחתי</h2>
          <button className="close-button" onClick={onCancel}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="child-join-form">
          <div className="form-group">
            <label htmlFor="joinCode">קוד הצטרפות:</label>
            <input
              type="text"
              inputMode="numeric"
              id="joinCode"
              className="join-code-input"
              value={joinCode}
              onChange={(e) => {
                const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
                setJoinCode(value);
                setError('');
              }}
              placeholder="הכנס קוד הצטרפות (6 תווים)"
              required
              autoFocus
              maxLength="6"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="child-join-buttons">
            <button 
              type="button" 
              className="cancel-button"
              onClick={onCancel}
            >
              ביטול
            </button>
            <button 
              type="submit" 
              className="join-submit-button"
              disabled={isLoading || joinCode.length !== 6}
            >
              {isLoading ? 'מצטרף...' : 'הצטרף'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChildJoin;

