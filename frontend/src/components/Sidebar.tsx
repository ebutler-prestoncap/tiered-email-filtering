import { NavLink, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import './Sidebar.css';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();

  // Close sidebar on mobile when route changes
  useEffect(() => {
    if (window.innerWidth < 1024) {
      onClose();
    }
  }, [location, onClose]);

  const navItems = [
    { path: '/', label: 'Process', icon: '📝' },
    { path: '/history', label: 'History', icon: '📊' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="sidebar-overlay" onClick={onClose} aria-hidden="true" />}
      
      {/* Sidebar */}
      <aside className={`sidebar ${isOpen ? 'open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-header">
          <h1 className="sidebar-title">Tiered Email Filtering</h1>
          <button
            className="sidebar-close"
            onClick={onClose}
            aria-label="Close sidebar"
            aria-expanded={isOpen}
          >
            ×
          </button>
        </div>
        
        <nav className="sidebar-nav" role="navigation">
          <ul className="sidebar-nav-list">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `sidebar-nav-link ${isActive ? 'active' : ''}`
                  }
                  end={item.path === '/'}
                >
                  <span className="sidebar-nav-icon">{item.icon}</span>
                  <span className="sidebar-nav-label">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </>
  );
}

