import React, { useState, useEffect } from 'react';

const BalanceDisplay = ({ balance, cashBoxBalance, childName, color, editable = false, onCashBoxUpdate }) => {
  const totalBalance = (balance || 0) + (cashBoxBalance || 0);
  const parentBalance = balance || 0;
  const [cashBoxValue, setCashBoxValue] = useState((cashBoxBalance || 0).toFixed(2));
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  // Update local state when cashBoxBalance prop changes
  useEffect(() => {
    setCashBoxValue((cashBoxBalance || 0).toFixed(2));
  }, [cashBoxBalance]);

  const handleCashBoxChange = (e) => {
    setCashBoxValue(e.target.value);
  };

  const handleCashBoxBlur = async () => {
    const newValue = parseFloat(cashBoxValue);
    if (isNaN(newValue) || newValue < 0) {
      // Reset to original value if invalid
      setCashBoxValue((cashBoxBalance || 0).toFixed(2));
      setIsEditing(false);
      return;
    }

    // Only update if value changed
    if (Math.abs(newValue - (cashBoxBalance || 0)) > 0.01) {
      setIsUpdating(true);
      try {
        if (onCashBoxUpdate) {
          await onCashBoxUpdate(newValue);
        }
      } catch (error) {
        console.error('Error updating cash box:', error);
        // Reset to original value on error
        setCashBoxValue((cashBoxBalance || 0).toFixed(2));
      } finally {
        setIsUpdating(false);
        setIsEditing(false);
      }
    } else {
      setIsEditing(false);
    }
  };

  const handleCashBoxFocus = () => {
    if (editable) {
      setIsEditing(true);
    }
  };

  const handleCashBoxKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.target.blur();
    } else if (e.key === 'Escape') {
      setCashBoxValue((cashBoxBalance || 0).toFixed(2));
      setIsEditing(false);
      e.target.blur();
    }
  };

  return (
    <div className="balance-display" style={{ borderColor: color }}>
      <h2 className="balance-label">יתרה של {childName}</h2>
      
      {/* Total Balance - Top */}
      <div className="total-balance-section">
        <div className="balance-label-small">יתרה כוללת</div>
        <div className="balance-amount" style={{ color: color }}>
          ₪{totalBalance.toFixed(2)}
        </div>
      </div>

      {/* Split Balance - Bottom */}
      <div className="split-balance-section">
        <div className="balance-split-item">
          <div className="balance-label-small">יתרה אצל ההורים</div>
          <div className="balance-amount-small" style={{ color: color }}>
            ₪{parentBalance.toFixed(2)}
          </div>
        </div>
        <div className="balance-split-item">
          <div className="balance-label-small">יתרה בקופה</div>
          {editable ? (
            <div className="cashbox-editable-wrapper">
              <span className="currency-symbol">₪</span>
              <input
                type="number"
                className="cashbox-input"
                value={cashBoxValue}
                onChange={handleCashBoxChange}
                onBlur={handleCashBoxBlur}
                onFocus={handleCashBoxFocus}
                onKeyDown={handleCashBoxKeyPress}
                step="0.01"
                min="0"
                disabled={isUpdating}
                style={{ color: color }}
              />
              {isUpdating && <span className="updating-indicator">...</span>}
            </div>
          ) : (
            <div className="balance-amount-small" style={{ color: color }}>
              ₪{(cashBoxBalance || 0).toFixed(2)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BalanceDisplay;

