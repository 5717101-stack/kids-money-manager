import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js';

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
  const colors = expensesByCategory.map(item => getCategoryColor(item.category));

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


