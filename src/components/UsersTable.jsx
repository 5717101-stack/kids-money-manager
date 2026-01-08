import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getAllUsers, deleteFamily, deleteChild } from '../utils/api';

const UsersTable = ({ onClose }) => {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getAllUsers();
      
      // Flatten the data structure
      const allUsers = [];
      
      if (data.families) {
        data.families.forEach(family => {
          // Add parents
          if (family.phoneNumber) {
            allUsers.push({
              id: `family_${family._id}`,
              name: `הורה - ${family.phoneNumber}`,
              type: 'הורה',
              firstConnection: family.createdAt || 'לא זמין',
              lastConnection: family.lastLoginAt || 'לא זמין',
              familyId: family._id,
              childId: null
            });
          }
          
          // Add children
          if (family.children && Array.isArray(family.children)) {
            family.children.forEach(child => {
              allUsers.push({
                id: `child_${child._id}`,
                name: child.name || 'ללא שם',
                type: 'ילד',
                firstConnection: child.createdAt || 'לא זמין',
                lastConnection: child.lastLoginAt || 'לא זמין',
                familyId: family._id,
                childId: child._id
              });
            });
          }
        });
      }
      
      setUsers(allUsers);
    } catch (err) {
      console.error('Error loading users:', err);
      setError(err.message || 'שגיאה בטעינת המשתמשים');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString || dateString === 'לא זמין') {
      return 'לא זמין';
    }
    try {
      const date = new Date(dateString);
      return date.toLocaleString('he-IL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateString;
    }
  };

  const handleSelectUser = (userId) => {
    const newSelected = new Set(selectedUsers);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUsers(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedUsers.size === users.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(users.map(u => u.id)));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedUsers.size === 0) {
      alert(t('admin.noSelection', { defaultValue: 'לא נבחרו משתמשים למחיקה' }));
      return;
    }

    const confirmMessage = t('admin.confirmDelete', { 
      defaultValue: `האם אתה בטוח שברצונך למחוק ${selectedUsers.size} משתמש/ים?`,
      count: selectedUsers.size
    });
    
    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      setDeleting(true);
      setError('');

      const deletePromises = [];
      for (const userId of selectedUsers) {
        const user = users.find(u => u.id === userId);
        if (!user) continue;

        if (user.type === 'הורה') {
          deletePromises.push(deleteFamily(user.familyId));
        } else if (user.type === 'ילד' && user.childId) {
          deletePromises.push(deleteChild(user.familyId, user.childId));
        }
      }

      await Promise.all(deletePromises);
      
      // Reload users after deletion
      await loadUsers();
      setSelectedUsers(new Set());
      
      alert(t('admin.deleteSuccess', { 
        defaultValue: `${selectedUsers.size} משתמש/ים נמחקו בהצלחה`,
        count: selectedUsers.size
      }));
    } catch (err) {
      console.error('Error deleting users:', err);
      setError(err.message || 'שגיאה במחיקת המשתמשים');
      alert(t('admin.deleteError', { defaultValue: 'שגיאה במחיקת המשתמשים' }));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="users-table-overlay" onClick={onClose}>
      <div className="users-table-container" onClick={(e) => e.stopPropagation()}>
        <div className="users-table-header">
          <h2>📊 {t('admin.usersTable', { defaultValue: 'טבלת משתמשים במערכת' })}</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>
        
        {loading && (
          <div className="users-table-loading">
            <p>{t('common.loading', { defaultValue: 'טוען נתונים...' })}</p>
          </div>
        )}
        
        {error && (
          <div className="users-table-error">
            <p>❌ {error}</p>
            <button onClick={loadUsers}>{t('common.retry', { defaultValue: 'נסה שוב' })}</button>
          </div>
        )}
        
        {!loading && !error && (
          <>
            <div className="users-table-info">
              <p>
                {t('admin.totalUsers', { defaultValue: 'סה"כ משתמשים' })}: <strong>{users.length}</strong>
                {selectedUsers.size > 0 && (
                  <span style={{ marginRight: '15px', color: '#ef4444' }}>
                    ({selectedUsers.size} {t('admin.selected', { defaultValue: 'נבחרו' })})
                  </span>
                )}
              </p>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={loadUsers} className="refresh-button">
                  🔄 {t('common.refresh', { defaultValue: 'רענן' })}
                </button>
                {selectedUsers.size > 0 && (
                  <button 
                    onClick={handleDeleteSelected} 
                    className="delete-button"
                    disabled={deleting}
                    style={{
                      background: '#ef4444',
                      color: 'white',
                      border: 'none',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: deleting ? 'not-allowed' : 'pointer',
                      opacity: deleting ? 0.6 : 1
                    }}
                  >
                    {deleting ? '⏳' : '🗑️'} {t('admin.deleteSelected', { defaultValue: 'מחק נבחרים' })}
                  </button>
                )}
              </div>
            </div>
            
            <div className="users-table-wrapper">
              <table className="users-table">
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}>
                      <input
                        type="checkbox"
                        checked={selectedUsers.size === users.length && users.length > 0}
                        onChange={handleSelectAll}
                        style={{ cursor: 'pointer' }}
                      />
                    </th>
                    <th>{t('admin.name', { defaultValue: 'שם' })}</th>
                    <th>{t('admin.type', { defaultValue: 'סוג' })}</th>
                    <th>{t('admin.firstConnection', { defaultValue: 'זמן חיבור ראשון' })}</th>
                    <th>{t('admin.lastConnection', { defaultValue: 'זמן שימוש אחרון' })}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>
                        {t('admin.noUsers', { defaultValue: 'אין משתמשים במערכת' })}
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => (
                      <tr key={user.id} style={{ 
                        backgroundColor: selectedUsers.has(user.id) ? '#fef2f2' : 'transparent' 
                      }}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedUsers.has(user.id)}
                            onChange={() => handleSelectUser(user.id)}
                            style={{ cursor: 'pointer' }}
                          />
                        </td>
                        <td>{user.name}</td>
                        <td>
                          <span className={`user-type-badge ${user.type === 'הורה' ? 'parent' : 'child'}`}>
                            {user.type}
                          </span>
                        </td>
                        <td>{formatDate(user.firstConnection)}</td>
                        <td>{formatDate(user.lastConnection)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default UsersTable;
