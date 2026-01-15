// Currency utility - returns currency symbol based on language
import i18n from '../i18n/config';

/**
 * Get currency symbol based on current language
 * @returns {string} Currency symbol (₪ for Hebrew, $ for English)
 */
export const getCurrencySymbol = () => {
  return i18n.language === 'he' ? '₪' : '$';
};

/**
 * Format amount with currency symbol based on language
 * @param {number} amount - The amount to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted amount with currency symbol
 */
export const formatCurrency = (amount, decimals = 2) => {
  const symbol = getCurrencySymbol();
  return `${symbol}${(amount || 0).toFixed(decimals)}`;
};
