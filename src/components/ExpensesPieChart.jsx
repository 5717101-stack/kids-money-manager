import React, { useState, useEffect, useMemo } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { useTranslation } from 'react-i18next';
import { getChildTransactions } from '../utils/api';

ChartJS.register(ArcElement, Tooltip, Legend);

const ExpensesPieChart = ({ familyId, children, categories }) => {
  const { t, i18n } = useTranslation();
  const [timeFilter, setTimeFilter] = useState('week'); // 'week' or 'month'
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expensesByCategory, setExpensesByCategory] = useState({});

  // Calculate date range based on filter
  const getDateRange = () => {
    const now = new Date();
    const startDate = new Date();
    
    if (timeFilter === 'week') {
      startDate.setDate(now.getDate() - 7);
    } else {
      startDate.setMonth(now.getMonth() - 1);
    }
    
    return { startDate, endDate: now };
  };

  // Load expenses from all children
  useEffect(() => {
    const loadExpenses = async () => {
      if (!familyId || !children || children.length === 0) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const { startDate, endDate } = getDateRange();
        const allExpenses = [];

        // Load transactions from all children
        for (const child of children) {
          try {
            // Load more transactions to ensure we get all expenses in the date range
            const transactions = await getChildTransactions(familyId, child._id, 100);
            
            // Filter expenses within date range
            const childExpenses = transactions.filter(t => {
              if (t.type !== 'expense') return false;
              const transactionDate = new Date(t.date || t.createdAt);
              return transactionDate >= startDate && transactionDate <= endDate;
            });

            // Add child info to each expense
            childExpenses.forEach(expense => {
              allExpenses.push({
                ...expense,
                childName: child.name,
                childId: child._id
              });
            });
          } catch (err) {
            console.error(`Error loading expenses for ${child.name}:`, err);
          }
        }

        // Group expenses by category
        const categoryTotals = {};
        allExpenses.forEach(expense => {
          const category = expense.category || t('parent.dashboard.other', { defaultValue: 'אחר' });
          if (!categoryTotals[category]) {
            categoryTotals[category] = {
              total: 0,
              transactions: []
            };
          }
          categoryTotals[category].total += Math.abs(expense.amount || 0);
          categoryTotals[category].transactions.push(expense);
        });

        setExpensesByCategory(categoryTotals);
        
        // If a category is selected, filter transactions
        if (selectedCategory) {
          setFilteredTransactions(categoryTotals[selectedCategory]?.transactions || []);
        } else {
          setFilteredTransactions([]);
        }
      } catch (error) {
        console.error('Error loading expenses:', error);
      } finally {
        setLoading(false);
      }
    };

    loadExpenses();
  }, [familyId, children, timeFilter, selectedCategory, t]);

  // Prepare chart data
  const chartData = useMemo(() => {
    const categoryNames = Object.keys(expensesByCategory);
    if (categoryNames.length === 0) {
      return null;
    }

    // Generate colors for categories
    const colors = [
      '#6366F1', '#8B5CF6', '#EC4899', '#F43F5E', '#EF4444',
      '#F59E0B', '#10B981', '#06B6D4', '#3B82F6', '#14B8A6'
    ];

    const data = categoryNames.map((category, index) => ({
      label: category,
      value: expensesByCategory[category].total,
      color: colors[index % colors.length]
    }));

    // Sort by value (descending)
    data.sort((a, b) => b.value - a.value);

    return {
      labels: data.map(d => d.label),
      datasets: [{
        data: data.map(d => d.value),
        backgroundColor: data.map(d => d.color),
        borderColor: '#ffffff',
        borderWidth: 2,
        hoverBorderWidth: 3
      }]
    };
  }, [expensesByCategory]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 15,
          font: {
            size: 12,
            weight: 500
          },
          usePointStyle: true,
          pointStyle: 'circle'
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ₪${value.toFixed(2)} (${percentage}%)`;
          }
        }
      }
    },
    onClick: (event, elements) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        const categoryName = chartData.labels[index];
        setSelectedCategory(categoryName);
      }
    }
  };

  const totalExpenses = Object.values(expensesByCategory).reduce((sum, cat) => sum + cat.total, 0);

  return (
    <div className="fintech-card" style={{ marginBottom: '20px' }}>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>
          {t('parent.dashboard.expensesByCategory', { defaultValue: 'הוצאות לפי קטגוריות' })}
        </h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => {
              setTimeFilter('week');
              setSelectedCategory(null);
            }}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: timeFilter === 'week' ? 'var(--primary-gradient)' : '#F3F4F6',
              color: timeFilter === 'week' ? 'white' : 'var(--text-main)',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            {t('parent.dashboard.week', { defaultValue: 'שבוע' })}
          </button>
          <button
            onClick={() => {
              setTimeFilter('month');
              setSelectedCategory(null);
            }}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: timeFilter === 'month' ? 'var(--primary-gradient)' : '#F3F4F6',
              color: timeFilter === 'month' ? 'white' : 'var(--text-main)',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            {t('parent.dashboard.month', { defaultValue: 'חודש' })}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid rgba(99, 102, 241, 0.2)',
            borderTopColor: '#6366F1',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }}></div>
        </div>
      ) : totalExpenses === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          {t('parent.dashboard.noExpenses', { defaultValue: 'אין הוצאות בתקופה זו' })}
        </div>
      ) : (
        <>
          <div style={{ height: '300px', marginBottom: '20px', position: 'relative' }}>
            {chartData && (
              <Pie data={chartData} options={chartOptions} />
            )}
          </div>

          {selectedCategory && expensesByCategory[selectedCategory] && (
            <div style={{
              marginTop: '20px',
              padding: '20px',
              background: '#F9FAFB',
              borderRadius: '12px',
              border: '2px solid var(--primary)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--primary)' }}>
                  {selectedCategory}
                </h3>
                <button
                  onClick={() => setSelectedCategory(null)}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '20px',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '4px 8px'
                  }}
                >
                  ✕
                </button>
              </div>
              <div style={{ marginBottom: '12px', fontSize: '16px', fontWeight: 600 }}>
                {t('parent.dashboard.total', { defaultValue: 'סה"כ' })}: ₪{expensesByCategory[selectedCategory].total.toFixed(2)}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                {filteredTransactions.map((transaction, index) => (
                  <div key={index} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px',
                    background: 'white',
                    borderRadius: '8px',
                    border: '1px solid rgba(0,0,0,0.05)'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>
                        {transaction.childName}
                      </div>
                      {transaction.description && (
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {transaction.description}
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        {new Date(transaction.date || transaction.createdAt).toLocaleDateString('he-IL', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#EF4444' }}>
                      -₪{Math.abs(transaction.amount || 0).toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ExpensesPieChart;
