import React from 'react';

const BalanceDisplay = ({ balance, childName, color }) => {
  return (
    <div className="balance-display" style={{ borderColor: color }}>
      <h2 className="balance-label">יתרה של {childName}</h2>
      <div className="balance-amount" style={{ color: color }}>
        ₪{balance.toFixed(2)}
      </div>
    </div>
  );
};

export default BalanceDisplay;

