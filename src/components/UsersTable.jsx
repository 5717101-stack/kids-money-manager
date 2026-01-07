import React, { useState, useEffect } from 'react';

const UsersTable = ({ onClose }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Get API URL
      const PRODUCTION_API = 'https://kids-money-manager-server.onrender.com/api';
      let apiUrl;
      
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        apiUrl = PRODUCTION_API;
      } else if (import.meta.env.VITE_API_URL) {
        apiUrl = import.meta.env.VITE_API_URL;
      } else if (import.meta.env.DEV) {
        apiUrl = 'http://localhost:3001/api';
      } else {
        apiUrl = PRODUCTION_API;
      }
      
      const response = await fetch(`${apiUrl}/admin/all-users`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Flatten the data structure
      const allUsers = [];
      
      if (data.families) {
        data.families.forEach(family => {
          // Add parents
          if (family.phoneNumber) {
            allUsers.push({
              name: `הורה - ${family.phoneNumber}`,
              type: 'הורה',
              firstConnection: family.createdAt || 'לא זמין',
              lastConnection: family.lastLoginAt || 'לא זמין',
              familyId: family._id
            });
          }
          
          // Add children
          if (family.children) {
            Object.values(family.children).forEach(child => {
              allUsers.push({
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

  return (
    <div className="users-table-overlay" onClick={onClose}>
      <div className="users-table-container" onClick={(e) => e.stopPropagation()}>
        <div className="users-table-header">
          <h2>📊 טבלת משתמשים במערכת</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>
        
        {loading && (
          <div className="users-table-loading">
            <p>טוען נתונים...</p>
          </div>
        )}
        
        {error && (
          <div className="users-table-error">
            <p>❌ {error}</p>
            <button onClick={loadUsers}>נסה שוב</button>
          </div>
        )}
        
        {!loading && !error && (
          <>
            <div className="users-table-info">
              <p>סה"כ משתמשים: <strong>{users.length}</strong></p>
              <button onClick={loadUsers} className="refresh-button">🔄 רענן</button>
            </div>
            
            <div className="users-table-wrapper">
              <table className="users-table">
                <thead>
                  <tr>
                    <th>שם</th>
                    <th>סוג</th>
                    <th>זמן חיבור ראשון</th>
                    <th>זמן שימוש אחרון</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '20px' }}>
                        אין משתמשים במערכת
                      </td>
                    </tr>
                  ) : (
                    users.map((user, index) => (
                      <tr key={index}>
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
