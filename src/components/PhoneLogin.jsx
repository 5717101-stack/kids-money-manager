import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { APP_VERSION } from '../constants';

const COUNTRY_CODES_HE = [
  { code: '+972', name: 'ישראל', flag: '🇮🇱' },
  { code: '+1', name: 'ארה"ב/קנדה', flag: '🇺🇸' },
  { code: '+44', name: 'בריטניה', flag: '🇬🇧' },
  { code: '+33', name: 'צרפת', flag: '🇫🇷' },
  { code: '+49', name: 'גרמניה', flag: '🇩🇪' },
  { code: '+39', name: 'איטליה', flag: '🇮🇹' },
  { code: '+34', name: 'ספרד', flag: '🇪🇸' },
  { code: '+7', name: 'רוסיה', flag: '🇷🇺' },
  { code: '+86', name: 'סין', flag: '🇨🇳' },
  { code: '+81', name: 'יפן', flag: '🇯🇵' },
  { code: '+91', name: 'הודו', flag: '🇮🇳' },
  { code: '+61', name: 'אוסטרליה', flag: '🇦🇺' },
  { code: '+27', name: 'דרום אפריקה', flag: '🇿🇦' },
  { code: '+971', name: 'איחוד האמירויות', flag: '🇦🇪' },
  { code: '+966', name: 'ערב הסעודית', flag: '🇸🇦' }
];

const COUNTRY_CODES_EN = [
  { code: '+972', name: 'Israel', flag: '🇮🇱' },
  { code: '+1', name: 'USA/Canada', flag: '🇺🇸' },
  { code: '+44', name: 'United Kingdom', flag: '🇬🇧' },
  { code: '+33', name: 'France', flag: '🇫🇷' },
  { code: '+49', name: 'Germany', flag: '🇩🇪' },
  { code: '+39', name: 'Italy', flag: '🇮🇹' },
  { code: '+34', name: 'Spain', flag: '🇪🇸' },
  { code: '+7', name: 'Russia', flag: '🇷🇺' },
  { code: '+86', name: 'China', flag: '🇨🇳' },
  { code: '+81', name: 'Japan', flag: '🇯🇵' },
  { code: '+91', name: 'India', flag: '🇮🇳' },
  { code: '+61', name: 'Australia', flag: '🇦🇺' },
  { code: '+27', name: 'South Africa', flag: '🇿🇦' },
  { code: '+971', name: 'UAE', flag: '🇦🇪' },
  { code: '+966', name: 'Saudi Arabia', flag: '🇸🇦' }
];

const PhoneLogin = ({ onOTPSent }) => {
  const { t, i18n } = useTranslation();
  const COUNTRY_CODES = i18n.language === 'he' ? COUNTRY_CODES_HE : COUNTRY_CODES_EN;
  const [selectedCountry, setSelectedCountry] = useState(COUNTRY_CODES[0]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCountryList, setShowCountryList] = useState(false);
  const phoneInputRef = useRef(null);

  const validatePhoneNumber = (phone) => {
    // Remove all non-digits
    const digitsOnly = phone.replace(/\D/g, '');
    // Check if it's a valid phone number (at least 7 digits, max 15)
    return digitsOnly.length >= 7 && digitsOnly.length <= 15;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clickTime = new Date().toISOString();
    
    console.log('========================================');
    console.log('[FRONTEND] 🎯 SEND OTP BUTTON CLICKED 🎯');
    console.log('[FRONTEND] ========================================');
    console.log('[FRONTEND] Timestamp:', clickTime);
    console.log('[FRONTEND] Country Code:', selectedCountry.code);
    console.log('[FRONTEND] Phone Number:', phoneNumber);
    console.log('[FRONTEND] ========================================\n');
    
    setError('');
    
    if (!phoneNumber || !validatePhoneNumber(phoneNumber)) {
      console.error('[FRONTEND] ❌ Phone validation failed');
      console.error('[FRONTEND] Phone:', phoneNumber);
      setError(t('auth.phoneLogin.invalidPhone', { defaultValue: 'מספר טלפון לא תקין' }));
      return;
    }

    const fullPhoneNumber = `${selectedCountry.code}${phoneNumber.replace(/\D/g, '')}`;
    console.log('[FRONTEND] ✅ Phone validation passed');
    console.log('[FRONTEND] Full Phone Number:', fullPhoneNumber);
    
    // Navigate to OTP screen immediately, OTP will be sent automatically in OTP screen
    onOTPSent(fullPhoneNumber, true); // Pass true as default, will be updated when OTP is sent
  };

  return (
    <div className="app-layout" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Language Toggle Button */}
      <button
        onClick={() => {
          const newLang = i18n.language === 'he' ? 'en' : 'he';
          i18n.changeLanguage(newLang);
        }}
        style={{
          position: 'fixed',
          top: 'max(16px, env(safe-area-inset-top))',
          right: i18n.language === 'he' ? '20px' : 'auto',
          left: i18n.language === 'he' ? 'auto' : '20px',
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          background: 'var(--primary-gradient)',
          border: 'none',
          color: 'white',
          fontSize: '20px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          zIndex: 10000,
          transition: 'transform 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.1)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        title={t('common.language', { defaultValue: 'שפה' })}
      >
        {i18n.language === 'he' ? '🇮🇱' : '🇬🇧'}
      </button>

      <div className="app-header">
        <div style={{ width: '44px' }}></div>
        <h1 className="header-title">
          {t('auth.phoneLogin.title', { defaultValue: 'הכנס מספר טלפון' })}
        </h1>
        <div style={{ width: '44px' }}></div>
      </div>

      <div className="content-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px', paddingTop: '20px' }}>
        <div className="fintech-card" style={{ maxWidth: '500px', width: '100%', margin: '0 auto' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', textAlign: 'center' }}>
            {t('auth.phoneLogin.subtitle', { defaultValue: 'נשלח לך קוד אימות ב-SMS' })}
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', gap: '10px', width: '100%', flexDirection: i18n.language === 'he' ? 'row-reverse' : 'row' }}>
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => setShowCountryList(!showCountryList)}
                  style={{
                    height: '50px',
                    width: '50px',
                    padding: '0',
                    borderRadius: '12px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    background: 'white',
                    fontSize: '24px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {selectedCountry.flag}
                </button>
                {showCountryList && (
                  <div 
                    dir={i18n.language === 'he' ? 'rtl' : 'ltr'}
                    style={{
                      position: 'fixed',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      marginTop: '0',
                      background: 'white',
                      borderRadius: '12px',
                      border: '1px solid rgba(0,0,0,0.1)',
                      boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                      maxHeight: '300px',
                      overflowY: 'auto',
                      zIndex: 1000,
                      minWidth: '250px',
                      width: 'auto',
                      maxWidth: '90vw'
                    }}
                  >
                    {COUNTRY_CODES.map((country) => (
                      <button
                        key={country.code}
                        type="button"
                        onClick={() => {
                          setSelectedCountry(country);
                          setShowCountryList(false);
                          // Focus on phone input after selecting country
                          setTimeout(() => {
                            if (phoneInputRef.current) {
                              phoneInputRef.current.focus();
                            }
                          }, 100);
                        }}
                        style={{
                          width: '100%',
                          padding: '12px 16px',
                          border: 'none',
                          background: 'transparent',
                          textAlign: i18n.language === 'he' ? 'right' : 'left',
                          cursor: 'pointer',
                          fontSize: '14px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          flexDirection: i18n.language === 'he' ? 'row-reverse' : 'row'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#F3F4F6'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <span style={{ fontSize: '20px' }}>{country.flag}</span>
                        <span style={{ fontWeight: 600 }}>{country.code}</span>
                        <span style={{ flex: 1 }}>{country.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <input
                ref={phoneInputRef}
                type="tel"
                value={phoneNumber}
                onChange={(e) => {
                  setPhoneNumber(e.target.value);
                  setError('');
                }}
                placeholder={t('auth.phoneLogin.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                required
                autoFocus
                inputMode="numeric"
                style={{
                  flex: 1,
                  minWidth: 0,
                  height: '50px',
                  padding: '0 16px',
                  borderRadius: '12px',
                  border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: '16px',
                  outline: 'none',
                  transition: '0.2s',
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.1)'}
              />
            </div>

            {error && (
              <div style={{
                padding: '12px 16px',
                borderRadius: '12px',
                background: '#FEE2E2',
                color: '#DC2626',
                fontSize: '14px',
                textAlign: 'center'
              }}>
                {error}
              </div>
            )}

            <button 
              type="submit" 
              disabled={isLoading || !phoneNumber}
              style={{
                width: '100%',
                height: '50px',
                borderRadius: '12px',
                background: isLoading || !phoneNumber ? '#ccc' : 'var(--primary-gradient)',
                color: 'white',
                border: 'none',
                fontSize: '16px',
                fontWeight: 600,
                cursor: isLoading || !phoneNumber ? 'not-allowed' : 'pointer',
                transition: '0.2s'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && phoneNumber) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 10px 20px rgba(99, 102, 241, 0.3)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {isLoading 
                ? t('auth.phoneLogin.sending', { defaultValue: 'שולח...' })
                : t('auth.phoneLogin.sendCode', { defaultValue: 'שלח קוד אימות' })}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: 'var(--text-muted)' }}>
          {t('common.version', { defaultValue: 'גרסה' })} {APP_VERSION}
        </div>
      </div>
    </div>
  );
};

export default PhoneLogin;
