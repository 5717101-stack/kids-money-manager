import React from 'react';

const TransactionList = ({ transactions, showAll = false }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('he-IL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (transactions.length === 0) {
    return (
      <div className="no-transactions">
        <p>אין פעולות עדיין</p>
      </div>
    );
  }

  return (
    <div className="transaction-list">
      <h2>{showAll ? 'כל הפעולות' : 'פעולות אחרונות'}</h2>
      <ul className="transactions">
        {transactions.map((transaction) => (
          <li key={transaction.id} className={`transaction ${transaction.type}`}>
            <div className="transaction-header">
              <div className="transaction-type-badge" style={{
                background: transaction.type === 'deposit' 
                  ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                  : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                color: 'white',
                padding: '8px 16px',
                borderRadius: '20px',
                fontSize: '14px',
                fontWeight: '700',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}>
                {transaction.type === 'deposit' ? '➕ הפקדה' : '➖ הוצאה'}
              </div>
              <span className="transaction-date">{formatDate(transaction.date)}</span>
            </div>
            <div className="transaction-details">
              <div className="transaction-amount" style={{
                color: transaction.type === 'deposit' ? '#22c55e' : '#ef4444',
                fontSize: '24px',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                direction: 'rtl'
              }}>
                <span>{transaction.type === 'deposit' ? '+' : '-'}</span>
                <span>₪{transaction.amount.toFixed(2)}</span>
              </div>
              <div className="transaction-meta">
                {transaction.description && (
                  <span className="transaction-description" style={{
                    fontSize: '16px',
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    marginBottom: '8px',
                    display: 'block'
                  }}>{transaction.description}</span>
                )}
                {transaction.category && (
                  <span className="transaction-category" style={{
                    display: 'inline-block',
                    padding: '6px 14px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    borderRadius: '20px',
                    fontSize: '13px',
                    fontWeight: '600',
                    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
                  }}>🏷️ {transaction.category}</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TransactionList;

