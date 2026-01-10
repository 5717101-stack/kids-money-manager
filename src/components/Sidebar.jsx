import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Settings from './Settings';
import LanguageToggle from './LanguageToggle';
import { APP_VERSION } from '../constants';

const Sidebar = ({ isOpen, onClose, familyId, onLogout, onChildrenUpdated, onMenuItemClick, childrenList = [], onChildDashboardClick }) => {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState(null);
  const [showChildrenSubmenu, setShowChildrenSubmenu] = useState(false);

  const menuItems = [
    {
      id: 'dashboard',
      label: t('sidebar.dashboard', { defaultValue: 'ממשק הורים' }),
      icon: '🏠'
    },
    {
      id: 'childrenDashboard',
      label: t('sidebar.childrenDashboard', { defaultValue: 'דשבורד ילדים' }),
      icon: '👦',
      hasSubmenu: true
    },
    {
      id: 'categories',
      label: t('sidebar.categories', { defaultValue: 'קטגוריות' }),
      icon: '🏷️'
    },
    {
      id: 'allowances',
      label: t('sidebar.allowances', { defaultValue: 'דמי כיס' }),
      icon: '💰'
    },
    {
      id: 'children',
      label: t('sidebar.childrenSettings', { defaultValue: 'הגדרת ילדים' }),
      icon: '👶'
    },
    {
      id: 'parents',
      label: t('sidebar.parents', { defaultValue: 'הגדרת הורים' }),
      icon: '👨‍👩‍👧‍👦'
    }
  ];

  const handleLogout = () => {
    if (window.confirm(t('sidebar.confirmLogout', { defaultValue: 'האם אתה בטוח שברצונך להתנתק?' }))) {
      onLogout();
      onClose();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className={`sidebar-overlay ${isOpen ? 'open' : ''}`}
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className={`sidebar-panel ${isOpen ? 'open' : ''}`} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ marginBottom: '30px' }}>
          <button 
            className="menu-btn"
            onClick={onClose}
            aria-label={t('common.close', { defaultValue: 'סגור' })}
            style={{ marginBottom: '20px' }}
          >
            ✕
          </button>
          <h2 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>
            {t('sidebar.title', { defaultValue: 'הגדרות' })}
          </h2>
        </div>

        <div className="sidebar-content" style={{ flex: 1, overflowY: 'auto' }}>
          <nav className="sidebar-nav" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {menuItems.map(item => (
              <div key={item.id}>
                <button
                  className={`sidebar-link ${activeTab === item.id ? 'active' : ''} ${item.hasSubmenu && showChildrenSubmenu ? 'submenu-open' : ''}`}
                  onClick={() => {
                    if (item.hasSubmenu) {
                      setShowChildrenSubmenu(!showChildrenSubmenu);
                    } else {
                      if (onMenuItemClick) {
                        onMenuItemClick(item.id);
                      } else {
                        setActiveTab(item.id);
                      }
                      setShowChildrenSubmenu(false);
                    }
                  }}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '12px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (activeTab !== item.id) {
                      e.currentTarget.style.background = '#F3F4F6';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== item.id) {
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  <span style={{ fontSize: '20px' }}>{item.icon}</span>
                  <span>{item.label}</span>
                  {item.hasSubmenu && (
                    <span style={{ marginLeft: 'auto' }}>{showChildrenSubmenu ? '▼' : '▶'}</span>
                  )}
                </button>
                {item.hasSubmenu && item.id === 'childrenDashboard' && showChildrenSubmenu && (
                  <div className="sidebar-submenu">
                    {childrenList.length === 0 ? (
                      <div className="sidebar-submenu-item disabled">
                        {t('sidebar.noChildren', { defaultValue: 'אין ילדים' })}
                      </div>
                    ) : (
                      childrenList.map(child => (
                        <button
                          key={child._id}
                          className="sidebar-submenu-item"
                          onClick={() => {
                            if (onChildDashboardClick) {
                              onChildDashboardClick(child);
                            }
                            setShowChildrenSubmenu(false);
                            onClose();
                          }}
                        >
                          <span className="sidebar-submenu-icon">
                            {child.profileImage ? (
                              <img src={child.profileImage} alt={child.name} className="sidebar-child-avatar" loading="lazy" decoding="async" />
                            ) : (
                              <span className="sidebar-child-initial">{child.name ? child.name.charAt(0).toUpperCase() : '?'}</span>
                            )}
                          </span>
                          <span className="sidebar-submenu-label">{child.name || ''}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            ))}
            
            {/* Language Toggle */}
            <div className="sidebar-language-toggle">
              <LanguageToggle />
            </div>
          </nav>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '30px', borderTop: '1px solid rgba(0,0,0,0.1)' }}>
          <button 
            className="sidebar-link"
            onClick={handleLogout}
            style={{ color: '#EF4444', fontWeight: 600 }}
          >
            <span style={{ fontSize: '20px' }}>🚪</span>
            <span>{t('common.logout', { defaultValue: 'התנתק' })}</span>
          </button>
          <div style={{ marginTop: '20px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
            {t('common.version', { defaultValue: 'גרסה' })} {APP_VERSION}
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
