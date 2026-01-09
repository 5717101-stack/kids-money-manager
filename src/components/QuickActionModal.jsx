import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { addTransaction } from '../utils/api';

const QuickActionModal = ({ familyId, children, categories, type, onClose, onComplete }) => {
  const { t, i18n } = useTranslation();
  // Check if a child was pre-selected from the child selector
  const preSelectedChildId = typeof window !== 'undefined' ? sessionStorage.getItem('selectedChildId') : null;
  const [selectedChildId, setSelectedChildId] = useState(preSelectedChildId || children[0]?._id || '');
  
  useEffect(() => {
    // Clear the pre-selected child from sessionStorage after using it
    if (preSelectedChildId && typeof window !== 'undefined') {
      sessionStorage.removeItem('selectedChildId');
    }
  }, [preSelectedChildId]);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Filter categories active for selected child
  const activeCategories = categories.filter(cat => 
    !selectedChildId || (cat.activeFor || []).includes(selectedChildId)
  ).map(cat => cat.name);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!amount || parseFloat(amount) <= 0) {
      alert(t('parent.dashboard.invalidAmount', { defaultValue: 'אנא הכנס סכום תקין' }));
      return;
    }

    if (!selectedChildId) {
      alert(t('parent.dashboard.selectChild', { defaultValue: 'אנא בחר ילד' }));
      return;
    }

    if (type === 'expense' && !category && activeCategories.length > 0) {
      alert(t('parent.dashboard.selectCategory', { defaultValue: 'אנא בחר קטגוריה' }));
      return;
    }

    try {
      setSubmitting(true);
      const transactionCategory = type === 'expense' ? category : null;
      await addTransaction(familyId, selectedChildId, type, amount, description, transactionCategory);
      
      // Reset form
      setAmount('');
      setDescription('');
      setCategory('');
      
      // Close modal and refresh
      onComplete();
      onClose();
    } catch (error) {
      alert(t('parent.dashboard.error', { defaultValue: 'שגיאה' }) + ': ' + error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      <div className="modal-content quick-action-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            {type === 'deposit' 
              ? t('parent.dashboard.addMoney', { defaultValue: 'הוסף כסף' })
              : t('parent.dashboard.recordExpense', { defaultValue: 'דווח הוצאה' })
            }
          </h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="quick-action-form">
          <div className="form-group">
            <label>{t('parent.dashboard.selectChild', { defaultValue: 'בחר ילד' })}:</label>
            <select
              value={selectedChildId}
              onChange={(e) => setSelectedChildId(e.target.value)}
              required
            >
              <option value="">{t('parent.dashboard.selectChild', { defaultValue: 'בחר ילד' })}</option>
              {children.map(child => (
                <option key={child._id} value={child._id}>{child.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>{t('parent.dashboard.amount', { defaultValue: 'סכום' })} (₪):</label>
            <input
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>

          {type === 'expense' && activeCategories.length > 0 && (
            <div className="form-group">
              <label>{t('parent.dashboard.category', { defaultValue: 'קטגוריה' })}:</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
              >
                <option value="">{t('parent.dashboard.selectCategory', { defaultValue: 'בחר קטגוריה' })}</option>
                {activeCategories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          )}

          <div className="form-group">
            <label>{t('parent.dashboard.description', { defaultValue: 'תיאור' })} (אופציונלי):</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('parent.dashboard.descriptionPlaceholder', { defaultValue: 'תיאור הפעולה' })}
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="cancel-button" onClick={onClose}>
              {t('common.cancel', { defaultValue: 'ביטול' })}
            </button>
            <button type="submit" className="submit-button" disabled={submitting}>
              {submitting 
                ? t('common.saving', { defaultValue: 'שומר...' })
                : t('common.confirm', { defaultValue: 'אישור' })
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickActionModal;
