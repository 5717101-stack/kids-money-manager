import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageToggle = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'he' ? 'en' : 'he';
    i18n.changeLanguage(newLang);
    
    // Update document direction
    document.documentElement.dir = newLang === 'he' ? 'rtl' : 'ltr';
    document.documentElement.lang = newLang;
  };

  return (
    <button
      className="language-toggle"
      onClick={toggleLanguage}
      title={i18n.language === 'he' ? 'Switch to English' : 'עבור לעברית'}
      style={{
        padding: '8px 12px',
        backgroundColor: 'transparent',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        cursor: 'pointer',
        fontSize: '14px',
        fontWeight: '600',
        color: 'var(--text-primary)',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        transition: 'all 0.2s ease'
      }}
    >
      {i18n.language === 'he' ? '🇮🇱' : '🇬🇧'} {i18n.language === 'he' ? 'עברית' : 'English'}
    </button>
  );
};

export default LanguageToggle;
