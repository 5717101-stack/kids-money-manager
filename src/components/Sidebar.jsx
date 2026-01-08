import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Settings from './Settings';

const Sidebar = ({ isOpen, onClose, familyId, onLogout, onChildrenUpdated }) => {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState('categories');

  const menuItems = [
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
      label: t('sidebar.children', { defaultValue: 'ילדים' }),
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
              <button
                key={item.id}
                className={`sidebar-nav-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => setActiveTab(item.id)}
              >
                <span className="sidebar-nav-icon">{item.icon}</span>
                <span className="sidebar-nav-label">{item.label}</span>
              </button>
            ))}
          </nav>

          {activeTab && (
            <div className="sidebar-settings-content">
              <Settings
                familyId={familyId}
                onClose={onClose}
                onLogout={onLogout}
                onChildrenUpdated={onChildrenUpdated}
                activeTab={activeTab}
                hideTabs={true}
                inSidebar={true}
              />
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <button 
            className="sidebar-logout-button"
            onClick={handleLogout}
          >
            <span className="sidebar-nav-icon">🚪</span>
            <span>{t('common.logout', { defaultValue: 'התנתק' })}</span>
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
