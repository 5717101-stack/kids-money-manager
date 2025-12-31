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
      <h3>{showAll ? 'כל הפעולות' : 'פעולות אחרונות'}</h3>
      <ul className="transactions">
        {transactions.map((transaction) => (
          <li key={transaction.id} className={`transaction ${transaction.type}`}>
            <div className="transaction-header">
              <span className="transaction-type">
                {transaction.type === 'deposit' ? '➕ הפקדה' : '➖ הוצאה'}
              </span>
              <span className="transaction-date">{formatDate(transaction.date)}</span>
            </div>
            <div className="transaction-details">
              <span className="transaction-amount" style={{
                color: transaction.type === 'deposit' ? '#22c55e' : '#ef4444'
              }}>
                {transaction.type === 'deposit' ? '+' : '-'}₪{transaction.amount.toFixed(2)}
              </span>
              <div className="transaction-meta">
                {transaction.description && (
                  <span className="transaction-description">{transaction.description}</span>
                )}
                {transaction.category && (
                  <span className="transaction-category">🏷️ {transaction.category}</span>
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

