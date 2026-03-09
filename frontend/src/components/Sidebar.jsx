/**
 * Sidebar Component — navigation panel with subject quick-access.
 * Knowledge Base is gated behind an admin PIN modal.
 */

import { useState, useCallback } from 'react';
import { APP_INFO, SUBJECTS } from '../utils/constants';
import api from '../api/client';
import './Sidebar.css';

function Sidebar({ collapsed, onToggle, activePage, onNavigate, studentInfo }) {
    const [showPinModal, setShowPinModal] = useState(false);
    const [pin, setPin] = useState('');
    const [pinError, setPinError] = useState('');
    const [verifying, setVerifying] = useState(false);

    // Check if admin is already unlocked this session
    const isAdminUnlocked = () => {
        return sessionStorage.getItem('admin_unlocked') === 'true';
    };

    // Handle Knowledge Base click
    const handleKBClick = useCallback(() => {
        if (isAdminUnlocked()) {
            onNavigate('documents');
        } else {
            setShowPinModal(true);
            setPin('');
            setPinError('');
        }
    }, [onNavigate]);

    // Handle PIN submission
    const handlePinSubmit = useCallback(async (e) => {
        e.preventDefault();
        if (!pin.trim()) {
            setPinError('Please enter the admin PIN');
            return;
        }

        setVerifying(true);
        setPinError('');

        try {
            const result = await api.verifyAdminPin(pin);
            if (result.success) {
                sessionStorage.setItem('admin_unlocked', 'true');
                setShowPinModal(false);
                setPin('');
                onNavigate('documents');
            } else {
                setPinError('Incorrect PIN. Access denied.');
                setPin('');
            }
        } catch (err) {
            setPinError('Verification failed. Please try again.');
        } finally {
            setVerifying(false);
        }
    }, [pin, onNavigate]);

    const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: '◈' },
        { id: 'study-mode', label: 'Study Mode', icon: '◆' },
        { id: 'study-plan', label: 'Study Plan', icon: '◎' },
        { id: 'documents', label: 'Knowledge Base', icon: '🔒', adminOnly: true },
        { id: 'chat', label: 'AI Chat', icon: '◉' },
        { id: 'settings', label: 'Settings', icon: '⚙' },
    ];

    return (
        <>
            <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
                {/* ── Brand ── */}
                <div className="sidebar__brand" onClick={() => onNavigate('landing')}>
                    <div className="sidebar__logo">
                        <span className="sidebar__logo-icon">✦</span>
                        {!collapsed && (
                            <div className="sidebar__logo-text">
                                <span className="sidebar__logo-name">{APP_INFO.name}</span>
                                <span className="sidebar__logo-tag">{APP_INFO.tagline}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Navigation ── */}
                <nav className="sidebar__nav">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            className={`sidebar__nav-item ${activePage === item.id ? 'sidebar__nav-item--active' : ''} ${item.adminOnly ? 'sidebar__nav-item--admin' : ''}`}
                            onClick={() => {
                                if (item.adminOnly) {
                                    handleKBClick();
                                } else {
                                    onNavigate(item.id);
                                }
                            }}
                            title={item.adminOnly ? `${item.label} (Admin)` : item.label}
                        >
                            <span className="sidebar__nav-icon">
                                {item.adminOnly ? (isAdminUnlocked() ? '◇' : '🔒') : item.icon}
                            </span>
                            {!collapsed && (
                                <span className="sidebar__nav-label">
                                    {item.label}
                                    {item.adminOnly && !collapsed && (
                                        <span className="sidebar__admin-badge">
                                            {isAdminUnlocked() ? '' : 'Admin'}
                                        </span>
                                    )}
                                </span>
                            )}
                        </button>
                    ))}
                </nav>

                {/* ── Subject Quick Access ── */}
                {!collapsed && (
                    <div className="sidebar__subjects">
                        <div className="sidebar__section-title">Subjects</div>
                        {Object.values(SUBJECTS).map((subject) => (
                            <button
                                key={subject.code}
                                className="sidebar__subject-item"
                                onClick={() => onNavigate('chat', { subjectCode: subject.code })}
                            >
                                <span className="sidebar__subject-icon">{subject.icon}</span>
                                <span className="sidebar__subject-name">{subject.shortName}</span>
                                <span
                                    className="sidebar__subject-dot"
                                    style={{ background: subject.color }}
                                />
                            </button>
                        ))}
                    </div>
                )}

                {/* ── Toggle Button ── */}
                <button
                    className="sidebar__toggle"
                    onClick={onToggle}
                    title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                    <span className={`sidebar__toggle-icon ${collapsed ? 'sidebar__toggle-icon--collapsed' : ''}`}>
                        ‹
                    </span>
                </button>

                {/* ── Footer ── */}
                {!collapsed && (
                    <div className="sidebar__footer">
                        {studentInfo && (
                            <div className="sidebar__student">
                                <span className="sidebar__student-avatar">👤</span>
                                <div className="sidebar__student-info">
                                    <span className="sidebar__student-name">{studentInfo.name}</span>
                                    <span className="sidebar__student-detail">
                                        {studentInfo.department} · Sec {studentInfo.section}
                                    </span>
                                </div>
                            </div>
                        )}
                        {!studentInfo && (
                            <>
                                <span className="sidebar__footer-text">
                                    {APP_INFO.department}
                                </span>
                                <span className="sidebar__footer-sub">
                                    {APP_INFO.year} · {APP_INFO.semester}
                                </span>
                            </>
                        )}
                    </div>
                )}
            </aside>

            {/* ── Admin PIN Modal ── */}
            {showPinModal && (
                <div className="pin-modal__overlay" onClick={() => setShowPinModal(false)}>
                    <div className="pin-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="pin-modal__header">
                            <span className="pin-modal__lock">🔐</span>
                            <h3 className="pin-modal__title">Admin Access</h3>
                            <p className="pin-modal__subtitle">
                                Enter the admin PIN to access the Knowledge Base
                            </p>
                        </div>

                        <form onSubmit={handlePinSubmit} className="pin-modal__form">
                            <div className="pin-modal__input-group">
                                <input
                                    type="password"
                                    value={pin}
                                    onChange={(e) => {
                                        setPin(e.target.value);
                                        setPinError('');
                                    }}
                                    placeholder="Enter PIN"
                                    className={`pin-modal__input ${pinError ? 'pin-modal__input--error' : ''}`}
                                    autoFocus
                                    maxLength={10}
                                />
                                {pinError && (
                                    <span className="pin-modal__error">{pinError}</span>
                                )}
                            </div>

                            <div className="pin-modal__actions">
                                <button
                                    type="button"
                                    className="pin-modal__btn pin-modal__btn--cancel"
                                    onClick={() => setShowPinModal(false)}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="pin-modal__btn pin-modal__btn--submit"
                                    disabled={verifying || !pin.trim()}
                                >
                                    {verifying ? 'Verifying...' : 'Unlock'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
}

export default Sidebar;
