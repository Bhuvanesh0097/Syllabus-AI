/**
 * Layout Component — App shell with sidebar and main content area.
 */

import { useState } from 'react';
import Sidebar from './Sidebar';
import './Layout.css';

function Layout({ children, activePage, onNavigate, studentInfo }) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    return (
        <div className="app-layout">
            <div className="bg-mesh" />
            <div className="bg-grid" />

            <Sidebar
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
                activePage={activePage}
                onNavigate={onNavigate}
                studentInfo={studentInfo}
            />

            <main
                className="main-content"
                style={{
                    marginLeft: sidebarCollapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)',
                }}
            >
                {children}
            </main>
        </div>
    );
}

export default Layout;
