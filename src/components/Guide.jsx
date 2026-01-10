import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const Guide = ({ userType = 'parent', onClose }) => {
  const { t, i18n } = useTranslation();
  const [currentStep, setCurrentStep] = useState(0);

  const guideSteps = userType === 'parent' 
    ? [
        {
          title: t('guide.parent.welcome.title', { defaultValue: 'ברוכים הבאים!' }),
          content: t('guide.parent.welcome.content', { defaultValue: 'אפליקציית ניהול כספי לילדים מאפשרת לכם לנהל את הכסף של הילדים שלכם בצורה נוחה ובטוחה.' }),
          icon: '👋'
        },
        {
          title: t('guide.parent.dashboard.title', { defaultValue: 'דשבורד הורים' }),
          content: t('guide.parent.dashboard.content', { defaultValue: 'בדשבורד תוכלו לראות את היתרה הכוללת של כל הילדים, פעילות אחרונה, וגרף הוצאות לפי קטגוריות.' }),
          icon: '📊'
        },
        {
          title: t('guide.parent.transactions.title', { defaultValue: 'הוספת פעולות' }),
          content: t('guide.parent.transactions.content', { defaultValue: 'השתמשו בכפתורים התחתונים להוספת כסף או דיווח הוצאה. בחרו ילד מהכפתור המרכזי.' }),
          icon: '💰'
        },
        {
          title: t('guide.parent.categories.title', { defaultValue: 'קטגוריות הוצאות' }),
          content: t('guide.parent.categories.content', { defaultValue: 'ניתן ליצור קטגוריות הוצאות מותאמות אישית. לחיצה על קטגוריה בגרף תציג רק את ההוצאות שלה.' }),
          icon: '🏷️'
        },
        {
          title: t('guide.parent.children.title', { defaultValue: 'ניהול ילדים' }),
          content: t('guide.parent.children.content', { defaultValue: 'הוסיפו ילדים חדשים, צפו בקודי הגישה שלהם, ועדכנו את פרטי הילדים.' }),
          icon: '👶'
        },
        {
          title: t('guide.parent.allowances.title', { defaultValue: 'דמי כיס' }),
          content: t('guide.parent.allowances.content', { defaultValue: 'הגדירו דמי כיס אוטומטיים שיתווספו ליתרה של הילדים בתדירות שתבחרו.' }),
          icon: '💵'
        }
      ]
    : [
        {
          title: t('guide.child.welcome.title', { defaultValue: 'שלום!' }),
          content: t('guide.child.welcome.content', { defaultValue: 'ברוכים הבאים לאפליקציית ניהול הכסף שלכם! כאן תוכלו לראות את היתרה שלכם ולנהל את הכסף.' }),
          icon: '👋'
        },
        {
          title: t('guide.child.balance.title', { defaultValue: 'יתרה' }),
          content: t('guide.child.balance.content', { defaultValue: 'בחלק העליון תראו את היתרה הכוללת שלכם, כולל הכסף אצל ההורים והכסף בקופה הפיזית.' }),
          icon: '💳'
        },
        {
          title: t('guide.child.transactions.title', { defaultValue: 'הוספת פעולות' }),
          content: t('guide.child.transactions.content', { defaultValue: 'השתמשו בכפתורים התחתונים להוספת הכנסה או דיווח הוצאה. הכפתור המרכזי הוא מחשבון.' }),
          icon: '💰'
        },
        {
          title: t('guide.child.history.title', { defaultValue: 'היסטוריה' }),
          content: t('guide.child.history.content', { defaultValue: 'בחלק "ההיסטוריה שלי" תראו את כל הפעולות שלכם. ניתן לסנן לפי קטגוריה או להגביל את מספר התצוגות.' }),
          icon: '📜'
        },
        {
          title: t('guide.child.goals.title', { defaultValue: 'מטרות חיסכון' }),
          content: t('guide.child.goals.content', { defaultValue: 'הגדירו מטרת חיסכון כדי לעקוב אחרי ההתקדמות שלכם. תראו כמה נשאר לחסוך כדי להגיע ליעד.' }),
          icon: '🎯'
        },
        {
          title: t('guide.child.expenses.title', { defaultValue: 'גרף הוצאות' }),
          content: t('guide.child.expenses.content', { defaultValue: 'הגרף מציג את ההוצאות שלכם לפי קטגוריות. לחיצה על קטגוריה תציג רק את ההוצאות שלה בהיסטוריה.' }),
          icon: '📊'
        }
      ];

  const handleNext = () => {
    if (currentStep < guideSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleFinish();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = () => {
    // Mark guide as seen
    localStorage.setItem(`guideSeen_${userType}`, 'true');
    if (onClose) {
      onClose();
    }
  };

  const handleSkip = () => {
    handleFinish();
  };

  return (
    <div className="modal-overlay" onClick={handleSkip}>
      <div className="modal-content guide-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px', width: '90%' }}>
        <div className="modal-header">
          <h2>{guideSteps[currentStep].title}</h2>
          <button className="close-button" onClick={handleSkip}>✕</button>
        </div>
        <div style={{ padding: '30px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>
            {guideSteps[currentStep].icon}
          </div>
          <p style={{ fontSize: '16px', lineHeight: '1.6', color: 'var(--text-main)', marginBottom: '30px' }}>
            {guideSteps[currentStep].content}
          </p>
          
          {/* Progress dots */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '30px' }}>
            {guideSteps.map((_, index) => (
              <div
                key={index}
                style={{
                  width: index === currentStep ? '24px' : '8px',
                  height: '8px',
                  borderRadius: '4px',
                  background: index === currentStep ? 'var(--primary)' : 'rgba(0,0,0,0.2)',
                  transition: 'all 0.3s'
                }}
              />
            ))}
          </div>

          {/* Navigation buttons */}
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            {currentStep > 0 && (
              <button
                onClick={handlePrevious}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: '#F3F4F6',
                  color: 'var(--text-main)',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t('guide.previous', { defaultValue: 'הקודם' })}
              </button>
            )}
            <button
              onClick={handleNext}
              style={{
                padding: '12px 24px',
                borderRadius: '12px',
                background: 'var(--primary-gradient)',
                color: 'white',
                border: 'none',
                fontSize: '16px',
                fontWeight: 600,
                cursor: 'pointer',
                flex: 1
              }}
            >
              {currentStep === guideSteps.length - 1 
                ? t('guide.finish', { defaultValue: 'סיום' })
                : t('guide.next', { defaultValue: 'הבא' })
              }
            </button>
          </div>
          <button
            onClick={handleSkip}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '14px',
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            {t('guide.skip', { defaultValue: 'דלג' })}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Guide;
