import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { archiveFamily } from '../utils/api';

const DeleteFamilyProfile = ({ familyId, onDeleteComplete, onCancel }) => {
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleDeleteClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmDelete = async () => {
    if (!familyId) {
      return;
    }

    setIsDeleting(true);
    
    try {
      await archiveFamily(familyId);
      
      // Show success notification
      const notification = document.createElement('div');
      notification.id = 'delete-family-notification';
      notification.innerHTML = `
        <div style="
          position: fixed;
          bottom: 20px;
          ${document.documentElement.dir === 'rtl' ? 'right' : 'left'}: 20px;
          background: linear-gradient(135deg, #10B981 0%, #059669 100%);
          color: white;
          padding: 16px 24px;
          border-radius: 16px;
          box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
          z-index: 10007;
          font-weight: 600;
          animation: slideIn 0.3s ease-out;
          max-width: 90%;
        ">
          ${t('deleteFamily.success', { defaultValue: 'הפרופיל המשפחתי נמחק בהצלחה' })}
        </div>
      `;
      document.body.appendChild(notification);

      // Remove notification after 3 seconds
      setTimeout(() => {
        if (notification.parentNode) {
          notification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => {
            if (notification.parentNode) {
              notification.parentNode.removeChild(notification);
            }
          }, 300);
        }
      }, 3000);

      // Call onDeleteComplete after a short delay
      setTimeout(() => {
        if (onDeleteComplete) {
          onDeleteComplete();
        }
      }, 1000);
    } catch (error) {
      setIsDeleting(false);
      setShowConfirm(false);
      
      // Show error notification
      const errorNotification = document.createElement('div');
      errorNotification.id = 'delete-family-error-notification';
      errorNotification.innerHTML = `
        <div style="
          position: fixed;
          bottom: 20px;
          ${document.documentElement.dir === 'rtl' ? 'right' : 'left'}: 20px;
          background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
          color: white;
          padding: 16px 24px;
          border-radius: 16px;
          box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
          z-index: 10007;
          font-weight: 600;
          animation: slideIn 0.3s ease-out;
          max-width: 90%;
        ">
          ${error.message || t('deleteFamily.error', { defaultValue: 'שגיאה במחיקת הפרופיל המשפחתי' })}
        </div>
      `;
      document.body.appendChild(errorNotification);

      // Remove notification after 5 seconds
      setTimeout(() => {
        if (errorNotification.parentNode) {
          errorNotification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => {
            if (errorNotification.parentNode) {
              errorNotification.parentNode.removeChild(errorNotification);
            }
          }, 300);
        }
      }, 5000);
    }
  };

  const handleCancel = () => {
    setShowConfirm(false);
    if (onCancel) {
      onCancel();
    }
  };

  return (
    <div className="app-layout" style={{ padding: '20px' }}>
      <div className="fintech-card" style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px', color: '#EF4444' }}>
          {t('deleteFamily.title', { defaultValue: 'מחיקת פרופיל משפחתי' })}
        </h2>

        {!showConfirm ? (
          <>
            <div style={{ marginBottom: '24px' }}>
              <div style={{ 
                background: '#FEF2F2', 
                border: '1px solid #FECACA', 
                borderRadius: '12px', 
                padding: '20px', 
                marginBottom: '20px' 
              }}>
                <p style={{ 
                  fontSize: '16px', 
                  lineHeight: '1.6', 
                  color: '#991B1B',
                  margin: 0 
                }}>
                  {t('deleteFamily.warning', { 
                    defaultValue: 'מחיקת הפרופיל המשפחתי תמחק את כל הנתונים וכל בני המשפחה המשויכים לפרופיל הזה. אין דרך לשחזר את הפרופיל או ההיסטוריה של הפעולות.' 
                  })}
                </p>
              </div>

              <div style={{ 
                background: '#F3F4F6', 
                borderRadius: '12px', 
                padding: '20px',
                marginBottom: '20px'
              }}>
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: 600, 
                  marginBottom: '12px',
                  color: '#1F2937'
                }}>
                  {t('deleteFamily.whatWillBeDeleted', { defaultValue: 'מה יימחק:' })}
                </h3>
                <ul style={{ 
                  margin: 0, 
                  paddingRight: '20px',
                  color: '#4B5563',
                  lineHeight: '1.8'
                }}>
                  <li>{t('deleteFamily.deleteChildren', { defaultValue: 'כל הילדים והנתונים שלהם' })}</li>
                  <li>{t('deleteFamily.deleteParents', { defaultValue: 'כל ההורים והנתונים שלהם' })}</li>
                  <li>{t('deleteFamily.deleteTransactions', { defaultValue: 'כל ההיסטוריה של הפעולות והעסקאות' })}</li>
                  <li>{t('deleteFamily.deleteCategories', { defaultValue: 'כל הקטגוריות וההגדרות' })}</li>
                  <li>{t('deleteFamily.deleteGoals', { defaultValue: 'כל המטרות והחיסכון' })}</li>
                </ul>
              </div>

              <div style={{ 
                background: '#EFF6FF', 
                border: '1px solid #BFDBFE', 
                borderRadius: '12px', 
                padding: '20px' 
              }}>
                <p style={{ 
                  fontSize: '14px', 
                  lineHeight: '1.6', 
                  color: '#1E40AF',
                  margin: 0 
                }}>
                  {t('deleteFamily.phoneNote', { 
                    defaultValue: 'מספרי הטלפון שהיו בשימוש יהיו פעילים עכשיו לשימוש לפרופילים אחרים.' 
                  })}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={handleCancel}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: 'transparent',
                  color: 'var(--text-main)',
                  border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t('common.cancel', { defaultValue: 'ביטול' })}
              </button>
              <button
                onClick={handleDeleteClick}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                  color: 'white',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                }}
              >
                {t('deleteFamily.deleteButton', { defaultValue: 'מחק פרופיל משפחתי' })}
              </button>
            </div>
          </>
        ) : (
          <>
            <div style={{ marginBottom: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
              <h3 style={{ 
                fontSize: '20px', 
                fontWeight: 600, 
                marginBottom: '12px',
                color: '#1F2937'
              }}>
                {t('deleteFamily.confirmTitle', { defaultValue: 'האם אתה בטוח?' })}
              </h3>
              <p style={{ 
                fontSize: '16px', 
                lineHeight: '1.6', 
                color: '#4B5563',
                margin: 0 
              }}>
                {t('deleteFamily.confirmMessage', { 
                  defaultValue: 'פעולה זו לא ניתנת לביטול. כל הנתונים יימחקו לצמיתות.' 
                })}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={handleCancel}
                disabled={isDeleting}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: 'transparent',
                  color: 'var(--text-main)',
                  border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: isDeleting ? 'not-allowed' : 'pointer',
                  opacity: isDeleting ? 0.5 : 1
                }}
              >
                {t('common.cancel', { defaultValue: 'ביטול' })}
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: isDeleting 
                    ? '#9CA3AF' 
                    : 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                  color: 'white',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: isDeleting ? 'not-allowed' : 'pointer',
                  boxShadow: isDeleting ? 'none' : '0 4px 12px rgba(239, 68, 68, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {isDeleting && (
                  <div style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid rgba(255, 255, 255, 0.3)',
                    borderTopColor: 'white',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite'
                  }}></div>
                )}
                {isDeleting 
                  ? t('deleteFamily.deleting', { defaultValue: 'מוחק...' })
                  : t('deleteFamily.confirmDelete', { defaultValue: 'כן, מחק' })
                }
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DeleteFamilyProfile;
