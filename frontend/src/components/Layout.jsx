/**
 * Layout Component — App shell with sidebar and main content area.
 * Includes mobile hamburger menu and overlay for responsive navigation.
 */

import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import './Layout.css';

function Layout({ children, activePage, onNavigate, studentInfo, canGoBack, onGoBack }) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    // Close mobile menu when navigating
    const handleNavigate = (page, params) => {
        setMobileMenuOpen(false);
        onNavigate(page, params);
    };

    // Close mobile menu on resize to desktop
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth > 768) {
                setMobileMenuOpen(false);
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Prevent body scroll when mobile menu is open
    useEffect(() => {
        if (mobileMenuOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [mobileMenuOpen]);

    return (
        <div className="app-layout">
            <div className="bg-mesh" />
            <div className="bg-grid" />

            {/* Mobile Header Bar */}
            <div className="mobile-header">
                {canGoBack ? (
                    <button
                        className="mobile-header__back-btn"
                        onClick={onGoBack}
                        aria-label="Go back"
                    >
                        ←
                    </button>
                ) : (
                    <button
                        className="mobile-header__menu-btn"
                        onClick={() => setMobileMenuOpen(true)}
                        aria-label="Open menu"
                    >
                        <span className="mobile-header__hamburger">
                            <span></span>
                            <span></span>
                            <span></span>
                        </span>
                    </button>
                )}
                <div className="mobile-header__brand">
                    <img src="/nexora-logo.png" alt="Nexora" className="mobile-header__logo" />
                    <span className="mobile-header__title">Nexora</span>
                </div>
                {canGoBack ? (
                    <button
                        className="mobile-header__menu-btn"
                        onClick={() => setMobileMenuOpen(true)}
                        aria-label="Open menu"
                    >
                        <span className="mobile-header__hamburger">
                            <span></span>
                            <span></span>
                            <span></span>
                        </span>
                    </button>
                ) : (
                    <div className="mobile-header__spacer" />
                )}
            </div>

            {/* Mobile Overlay */}
            {mobileMenuOpen && (
                <div
                    className="mobile-overlay"
                    onClick={() => setMobileMenuOpen(false)}
                />
            )}

            <Sidebar
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
                activePage={activePage}
                onNavigate={handleNavigate}
                studentInfo={studentInfo}
                mobileOpen={mobileMenuOpen}
                onMobileClose={() => setMobileMenuOpen(false)}
            />

            <main
                className="main-content"
                style={{
                    marginLeft: sidebarCollapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)',
                }}
            >
                {canGoBack && (
                    <button
                        className="main-content__back-btn"
                        onClick={onGoBack}
                        aria-label="Go back"
                        title="Go back"
                    >
                        <span className="main-content__back-arrow">←</span>
                        <span className="main-content__back-label">Back</span>
                    </button>
                )}
                {children}
            </main>
        </div>
    );
}

export default Layout;
