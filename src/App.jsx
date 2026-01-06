import React, { useState, useEffect } from 'react';
import ParentDashboard from './components/ParentDashboard';
import ParentLogin from './components/ParentLogin';
import ChildView from './components/ChildView';

const App = () => {
  const [view, setView] = useState('parent'); // 'parent', 'child1', 'child2'
  const [isParentLoggedIn, setIsParentLoggedIn] = useState(false);

  useEffect(() => {
    // Check if parent is already logged in (from sessionStorage)
    const loggedIn = sessionStorage.getItem('parentLoggedIn') === 'true';
    setIsParentLoggedIn(loggedIn);
  }, []);

  const handleParentLogin = () => {
    setIsParentLoggedIn(true);
  };

  const handleParentViewClick = () => {
    // If not logged in, show login screen
    if (!isParentLoggedIn) {
      setView('parent');
    } else {
      setView('parent');
    }
  };

  return (
    <div className="app">
      <nav className="main-nav">
        <button
          className={view === 'parent' ? 'active' : ''}
          onClick={handleParentViewClick}
        >
          👨‍👩‍👧‍👦 ממשק הורה
        </button>
        <button
          className={view === 'child1' ? 'active' : ''}
          onClick={() => setView('child1')}
        >
          👦 אדם
        </button>
        <button
          className={view === 'child2' ? 'active' : ''}
          onClick={() => setView('child2')}
        >
          👧 ג'וּן
        </button>
      </nav>

      <main className="main-content">
        {view === 'parent' && (
          isParentLoggedIn ? (
            <ParentDashboard />
          ) : (
            <ParentLogin onLogin={handleParentLogin} />
          )
        )}
        {view === 'child1' && <ChildView childId="child1" />}
        {view === 'child2' && <ChildView childId="child2" />}
      </main>
      
      <footer className="app-footer">
        <span className="version">גרסה 2.4</span>
      </footer>
    </div>
  );
};

export default App;

