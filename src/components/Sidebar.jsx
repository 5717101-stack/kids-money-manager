import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Settings from './Settings';
import LanguageToggle from './LanguageToggle';

// Get version from package.json
const VERSION = '3.4.51';

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
      id: 'profileImages',
      label: t('sidebar.profile', { defaultValue: 'פרופיל' }),
      icon: '👤'
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
      label: t('sidebar.parents', { defaultValue: 'הורים' }),
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
      {isOpen && (
        <div 
          className="sidebar-backdrop" 
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <button 
            className="sidebar-close-button"
            onClick={onClose}
            aria-label={t('common.close', { defaultValue: 'סגור' })}
          >
            ✕
          </button>
          <h2 className="sidebar-title">
            {t('sidebar.title', { defaultValue: 'הגדרות' })}
          </h2>
        </div>

        <div className="sidebar-content">
          <nav className="sidebar-nav">
            {menuItems.map(item => (
              <div key={item.id}>
                <button
                  className={`sidebar-nav-item ${activeTab === item.id ? 'active' : ''} ${item.hasSubmenu && showChildrenSubmenu ? 'submenu-open' : ''}`}
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
                >
                  <span className="sidebar-nav-icon">{item.icon}</span>
                  <span className="sidebar-nav-label">{item.label}</span>
                  {item.hasSubmenu && (
                    <span className="sidebar-submenu-arrow">{showChildrenSubmenu ? '▼' : '▶'}</span>
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
                              <img src={child.profileImage} alt={child.name} className="sidebar-child-avatar" />
                            ) : (
                              <span className="sidebar-child-initial">{child.name.charAt(0).toUpperCase()}</span>
                            )}
                          </span>
                          <span className="sidebar-submenu-label">{child.name}</span>
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

        <div className="sidebar-footer">
          <button 
            className="sidebar-logout-button"
            onClick={handleLogout}
          >
            <span className="sidebar-nav-icon">🚪</span>
            <span>{t('common.logout', { defaultValue: 'התנתק' })}</span>
          </button>
          <div className="sidebar-version">
            {t('common.version', { defaultValue: 'גרסה' })} {VERSION}
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
