import React from 'react';

const BalanceDisplay = ({ balance, cashBoxBalance, childName, color }) => {
  const totalBalance = (balance || 0) + (cashBoxBalance || 0);
  const parentBalance = balance || 0;
  const cashBox = cashBoxBalance || 0;

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
          <div className="balance-amount-small" style={{ color: color }}>
            ₪{cashBox.toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BalanceDisplay;

