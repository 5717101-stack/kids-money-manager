import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { useTranslation } from 'react-i18next';
import { getChildTransactions } from '../utils/api';
import { getCached, setCached } from '../utils/cache';

ChartJS.register(ArcElement, Tooltip, Legend);

// Default colors palette for categories
const DEFAULT_COLORS = [
  '#3b82f6', // כחול
  '#ec4899', // ורוד
  '#10b981', // ירוק
  '#f59e0b', // כתום
  '#8b5cf6', // סגול
  '#ef4444', // אדום
  '#06b6d4', // ציאן
  '#f97316', // כתום כהה
  '#84cc16', // ירוק ליים
  '#a855f7', // סגול כהה
  '#14b8a6', // טורקיז
  '#f43f5e', // ורוד כהה
  '#6366f1', // אינדיגו
  '#22c55e', // ירוק בהיר
  '#eab308'  // צהוב
];

// Legacy category colors for backward compatibility (fixed colors)
const CATEGORY_COLORS = {
  'משחקים': '#3b82f6',
  'ממתקים': '#ec4899',
  'בגדים': '#10b981',
  'בילויים': '#f59e0b',
  'אחר': '#6b7280'
};

// Cache for category colors to ensure consistency
const categoryColorCache = { ...CATEGORY_COLORS };

// Simple hash function to convert string to number
const hashString = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash);
};

// Generate consistent color for a category based on its name
const getCategoryColor = (category) => {
  // If it's already in cache, use cached color
  if (categoryColorCache.hasOwnProperty(category)) {
    return categoryColorCache[category];
  }
  
  // Generate a consistent color based on the category name hash
  const hash = hashString(category);
  const colorIndex = hash % DEFAULT_COLORS.length;
  const color = DEFAULT_COLORS[colorIndex];
  
  // Cache it for future use
  categoryColorCache[category] = color;
  
  return color;
};

const ExpensesPieChart = ({ familyId, children, categories, onCategorySelect, selectedCategory, forceReload }) => {
  const { t, i18n } = useTranslation();
  const [timeFilter, setTimeFilter] = useState('week'); // 'week' or 'month'
  const [loading, setLoading] = useState(true);
  const [expensesByCategory, setExpensesByCategory] = useState([]);

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

  const lastForceReloadRef = useRef(forceReload);
  const childrenIdsRef = useRef(children?.map(c => c._id).join(',') || '');

  // Load expenses from all children (with caching)
  useEffect(() => {
    let isMounted = true;
    
    const loadExpenses = async () => {
      // Always set loading to false if no data
      if (!familyId || !children || children.length === 0) {
        if (isMounted) {
          setLoading(false);
          setExpensesByCategory([]);
        }
        return;
      }

      // Create cache key based on familyId, children IDs, and timeFilter
      const childrenIds = children.map(c => c._id || c.id).filter(Boolean).sort().join(',');
      if (!childrenIds) {
        if (isMounted) {
          setLoading(false);
          setExpensesByCategory([]);
        }
        return;
      }
      
      const cacheKey = `expenses_chart_${familyId}_${childrenIds}_${timeFilter}`;
      const cacheTTL = 10 * 60 * 1000; // 10 minutes cache

      // Check if we need to reload (forceReload changed or children changed)
      const forceReloadChanged = lastForceReloadRef.current !== forceReload;
      const childrenChanged = childrenIdsRef.current !== childrenIds;
      
      // Check cache first (unless force reload or children changed)
      if (!forceReloadChanged && !childrenChanged) {
        try {
          const cached = getCached(cacheKey, cacheTTL);
          if (cached !== null && isMounted) {
            setExpensesByCategory(cached);
            setLoading(false);
            return;
          }
        } catch (cacheError) {
          console.warn('Cache read error:', cacheError);
          // Continue to load from API
        }
      }

      // Update refs
      lastForceReloadRef.current = forceReload;
      childrenIdsRef.current = childrenIds;

      try {
        if (isMounted) {
          setLoading(true);
        }
        
        const { startDate, endDate } = getDateRange();
        const allExpenses = [];

        // Load transactions from all children
        for (const child of children) {
          if (!isMounted) break;
          
          try {
            const childId = child._id || child.id;
            if (!childId) continue;
            
            // Load ALL transactions (no limit) to ensure we get all expenses in the date range
            const transactions = await getChildTransactions(familyId, childId, null);
            
            if (!isMounted) break;
            
            // Filter expenses within date range
            const childExpenses = (transactions || []).filter(t => {
              if (!t || t.type !== 'expense') return false;
              try {
                const transactionDate = new Date(t.date || t.createdAt);
                return transactionDate >= startDate && transactionDate <= endDate;
              } catch (dateError) {
                return false;
              }
            });

            // Add child info to each expense
            childExpenses.forEach(expense => {
              allExpenses.push({
                ...expense,
                childName: child.name,
                childId: childId
              });
            });
          } catch (err) {
            console.error(`Error loading expenses for ${child.name || childId}:`, err);
            // Continue with other children
          }
        }

        if (!isMounted) return;

        // Group expenses by category
        const categoryTotals = {};
        allExpenses.forEach(expense => {
          const category = expense.category || t('parent.dashboard.other', { defaultValue: 'אחר' });
          if (!categoryTotals[category]) {
            categoryTotals[category] = 0;
          }
          categoryTotals[category] += Math.abs(expense.amount || 0);
        });

        // Convert to array format like ExpensePieChart expects
        const expensesArray = Object.keys(categoryTotals).map(category => ({
          category: category,
          amount: categoryTotals[category]
        })).sort((a, b) => b.amount - a.amount); // Sort by amount descending

        // Cache the result
        try {
          setCached(cacheKey, expensesArray, cacheTTL);
        } catch (cacheError) {
          console.warn('Cache write error:', cacheError);
        }
        
        if (isMounted) {
          setExpensesByCategory(expensesArray);
        }
      } catch (error) {
        console.error('Error loading expenses:', error);
        if (isMounted) {
          setExpensesByCategory([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadExpenses();
    
    return () => {
      isMounted = false;
    };
    // Only reload when timeFilter changes, when children list changes (new child added), or when forceReload is triggered
    // Don't reload automatically on interval - only when explicitly needed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyId, timeFilter, t, forceReload, children]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!expensesByCategory || expensesByCategory.length === 0) {
      return null;
    }

    const labels = expensesByCategory.map(item => item.category);
    const data = expensesByCategory.map(item => item.amount);
    const colors = expensesByCategory.map(item => getCategoryColor(item.category));

    return {
      labels: labels,
      datasets: [{
        label: 'סכום (₪)',
        data: data,
        backgroundColor: colors,
        borderColor: colors.map(c => c + 'CC'),
        borderWidth: 2
      }]
    };
  }, [expensesByCategory]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      animateRotate: true,
      animateScale: true,
      duration: 2000,
      easing: 'easeOutQuart'
    },
    plugins: {
      legend: {
        display: false // Hide default legend - we'll show custom list
      },
      tooltip: {
        enabled: false // Disable tooltip on click/hover
      }
    },
    elements: {
      arc: {
        borderWidth: 4,
        borderColor: '#ffffff',
        hoverBorderWidth: 6,
        hoverOffset: 12,
        borderRadius: 8
      }
    },
    interaction: {
      intersect: false,
      mode: 'point'
    },
    onClick: (event, elements) => {
      if (elements.length > 0 && chartData) {
        const index = elements[0].index;
        const categoryName = chartData.labels[index];
        // Toggle: if same category clicked, deselect it
        if (onCategorySelect) {
          if (selectedCategory === categoryName) {
            onCategorySelect(null);
          } else {
            onCategorySelect(categoryName);
          }
        }
      }
    }
  };

  // Calculate total and percentages for display
  const total = expensesByCategory.reduce((sum, item) => sum + item.amount, 0);
  const categoriesWithDetails = expensesByCategory.map((item) => ({
    category: item.category,
    amount: item.amount,
    percentage: total > 0 ? ((item.amount / total) * 100).toFixed(1) : '0',
    color: getCategoryColor(item.category)
  }));

  const days = timeFilter === 'week' ? 7 : 30;

  return (
    <div className="fintech-card">
      <div className="expenses-chart-header">
        <h2>{t('parent.dashboard.expensesByCategory', { defaultValue: 'הוצאות לפי קטגוריות' })}</h2>
        <div className="period-toggle">
          <button
            className={`period-button ${timeFilter === 'week' ? 'active' : ''}`}
            onClick={() => {
              setTimeFilter('week');
              if (onCategorySelect) {
                onCategorySelect(null);
              }
            }}
          >
            {t('parent.dashboard.week', { defaultValue: 'שבוע' })}
          </button>
          <button
            className={`period-button ${timeFilter === 'month' ? 'active' : ''}`}
            onClick={() => {
              setTimeFilter('month');
              if (onCategorySelect) {
                onCategorySelect(null);
              }
            }}
          >
            {t('parent.dashboard.month', { defaultValue: 'חודש' })}
          </button>
        </div>
      </div>
      {loading ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 20px',
          gap: '16px'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid rgba(99, 102, 241, 0.2)',
            borderTopColor: '#6366F1',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }}></div>
        </div>
      ) : expensesByCategory.length === 0 ? (
        <div className="no-data-message">
          <p>{t('parent.dashboard.noExpenses', { defaultValue: 'אין הוצאות בתקופה זו' })}</p>
        </div>
      ) : (
        <div className="expense-distribution-container">
          <div className="expense-chart-wrapper">
            <div className="expense-pie-chart">
              {chartData && <Pie data={chartData} options={chartOptions} />}
            </div>
          </div>
          <div className="expense-categories-list">
            {categoriesWithDetails.map((item, index) => (
              <div 
                key={index} 
                className={`expense-category-item ${selectedCategory === item.category ? 'selected' : ''}`}
                onClick={() => {
                  if (onCategorySelect) {
                    if (selectedCategory === item.category) {
                      onCategorySelect(null);
                    } else {
                      onCategorySelect(item.category);
                    }
                  }
                }}
                style={{ cursor: 'pointer' }}
              >
                <div className="category-color-indicator" style={{ backgroundColor: item.color }}></div>
                <div className="category-info">
                  <div className="category-name">{item.category}</div>
                  <div className="category-amount">₪{item.amount.toFixed(2)}</div>
                </div>
                <div className="category-percentage">{item.percentage}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpensesPieChart;
