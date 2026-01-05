import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

// Default colors for categories
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
  '#ec4899'  // ורוד
];

// Legacy category colors for backward compatibility
const CATEGORY_COLORS = {
  'משחקים': '#3b82f6',
  'ממתקים': '#ec4899',
  'בגדים': '#10b981',
  'בילויים': '#f59e0b',
  'אחר': '#6b7280'
};

// Generate color for a category
const getCategoryColor = (category, index) => {
  // If it's a known category, use its color
  if (CATEGORY_COLORS.hasOwnProperty(category)) {
    return CATEGORY_COLORS[category];
  }
  // Otherwise, use a color from the default palette based on index
  return DEFAULT_COLORS[index % DEFAULT_COLORS.length];
};

const ExpensePieChart = ({ expensesByCategory, title, days }) => {
  if (!expensesByCategory || expensesByCategory.length === 0) {
    return (
      <div className="chart-container">
        <h3>{title}</h3>
        <div className="no-data-message">
          <p>אין הוצאות ב-{days} הימים האחרונים</p>
        </div>
      </div>
    );
  }

  const labels = expensesByCategory.map(item => item.category);
  const data = expensesByCategory.map(item => item.amount);
  const colors = expensesByCategory.map((item, index) => getCategoryColor(item.category, index));

  const chartData = {
    labels: labels,
    datasets: [
      {
        label: 'סכום (₪)',
        data: data,
        backgroundColor: colors,
        borderColor: colors.map(c => c + 'CC'),
        borderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        rtl: true,
        labels: {
          padding: 15,
          font: {
            size: 14,
            family: 'Arial, sans-serif'
          }
        }
      },
      tooltip: {
        rtl: true,
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
    }
  };

  return (
    <div className="chart-container">
      <h3>{title}</h3>
      <div className="chart-wrapper">
        <Pie data={chartData} options={options} />
      </div>
    </div>
  );
};

export default ExpensePieChart;


