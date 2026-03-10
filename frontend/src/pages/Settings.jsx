/**
 * Settings Page — Tone customization, Dark Mode toggle, and About section.
 */

import { useState, useEffect, useCallback } from 'react';
import { APP_INFO } from '../utils/constants';
import './Settings.css';

const TONES = [
    { id: 'professional', label: 'Professional', icon: '💼', desc: 'Formal and structured responses' },
    { id: 'friendly', label: 'Friendly', icon: '😊', desc: 'Warm and approachable style' },
    { id: 'simple', label: 'Simple', icon: '✨', desc: 'Easy-to-understand language' },
    { id: 'motivational', label: 'Motivational', icon: '🔥', desc: 'Encouraging and uplifting' },
    { id: 'teacher', label: 'Teacher Style', icon: '👨‍🏫', desc: 'Step-by-step teaching approach' },
    { id: 'exam_prep', label: 'Exam Prep', icon: '📝', desc: 'Exam-focused and structured' },
    { id: 'concise', label: 'Concise', icon: '⚡', desc: 'Short, to-the-point answers' },
    { id: 'detailed', label: 'Detailed', icon: '📖', desc: 'Thorough, in-depth explanations' },
    { id: 'supportive', label: 'Supportive', icon: '🤝', desc: 'Patient and reassuring' },
    { id: 'calm', label: 'Calm', icon: '🧘', desc: 'Relaxed, stress-free tone' },
];

function Settings({ settings: appSettings, onUpdateSettings }) {
    const [selectedTone, setSelectedTone] = useState(appSettings?.tone || 'professional');
    const [darkMode, setDarkMode] = useState(appSettings?.darkMode !== false);
    const [saved, setSaved] = useState(false);

    // Sync from parent
    useEffect(() => {
        if (appSettings?.tone) setSelectedTone(appSettings.tone);
        if (appSettings?.darkMode !== undefined) setDarkMode(appSettings.darkMode);
    }, [appSettings]);

    const handleToneChange = useCallback((toneId) => {
        setSelectedTone(toneId);
        onUpdateSettings?.({ tone: toneId, darkMode });
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    }, [darkMode, onUpdateSettings]);

    const handleDarkModeToggle = useCallback(() => {
        const newMode = !darkMode;
        setDarkMode(newMode);
        onUpdateSettings?.({ tone: selectedTone, darkMode: newMode });
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    }, [darkMode, selectedTone, onUpdateSettings]);

    return (
        <div className="settings">
            {/* Save Indicator */}
            {saved && (
                <div className="settings__saved animate-fade-in">
                    ✓ Settings saved
                </div>
            )}

            <div className="settings__header">
                <h1 className="settings__title">⚙️ Settings</h1>
                <p className="settings__subtitle">Customize your study experience</p>
            </div>

            <div className="settings__grid">
                {/* ── Tone Customization ── */}
                <section className="settings__section settings__section--tone">
                    <div className="settings__section-header">
                        <h2 className="settings__section-title">🎨 AI Tone</h2>
                        <p className="settings__section-desc">
                            Choose how the AI communicates with you
                        </p>
                    </div>

                    <div className="settings__tone-grid">
                        {TONES.map((tone) => (
                            <button
                                key={tone.id}
                                className={`settings__tone-card ${selectedTone === tone.id ? 'settings__tone-card--active' : ''}`}
                                onClick={() => handleToneChange(tone.id)}
                            >
                                <span className="settings__tone-icon">{tone.icon}</span>
                                <div className="settings__tone-info">
                                    <span className="settings__tone-name">{tone.label}</span>
                                    <span className="settings__tone-desc">{tone.desc}</span>
                                </div>
                                {selectedTone === tone.id && (
                                    <span className="settings__tone-check">✓</span>
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="settings__tone-preview">
                        <span className="settings__preview-label">Active Tone</span>
                        <span className="settings__preview-value">
                            {TONES.find(t => t.id === selectedTone)?.icon}{' '}
                            {TONES.find(t => t.id === selectedTone)?.label}
                        </span>
                    </div>
                </section>

                {/* ── Dark Mode ── */}
                <section className="settings__section settings__section--appearance">
                    <div className="settings__section-header">
                        <h2 className="settings__section-title">🌙 Appearance</h2>
                        <p className="settings__section-desc">
                            Switch between dark and light mode
                        </p>
                    </div>

                    <div className="settings__toggle-row">
                        <div className="settings__toggle-info">
                            <span className="settings__toggle-label">
                                {darkMode ? '🌙 Dark Mode' : '☀️ Light Mode'}
                            </span>
                            <span className="settings__toggle-desc">
                                {darkMode
                                    ? 'Easy on the eyes for night studying'
                                    : 'Bright theme for daytime use'}
                            </span>
                        </div>
                        <button
                            className={`settings__toggle-switch ${darkMode ? 'settings__toggle-switch--on' : ''}`}
                            onClick={handleDarkModeToggle}
                            aria-label="Toggle dark mode"
                        >
                            <span className="settings__toggle-knob" />
                        </button>
                    </div>

                    <div className="settings__mode-preview">
                        <div className={`settings__mode-card ${darkMode ? 'settings__mode-card--dark' : 'settings__mode-card--light'}`}>
                            <div className="settings__mode-bar" />
                            <div className="settings__mode-line settings__mode-line--wide" />
                            <div className="settings__mode-line settings__mode-line--medium" />
                            <div className="settings__mode-line settings__mode-line--narrow" />
                        </div>
                    </div>
                </section>

                {/* ── About Section ── */}
                <section className="settings__section settings__section--about">
                    <div className="settings__section-header">
                        <h2 className="settings__section-title">ℹ️ About</h2>
                        <p className="settings__section-desc">
                            Project information and credits
                        </p>
                    </div>

                    <div className="settings__about-card">
                        <div className="settings__about-logo">
                            <span className="settings__about-logo-icon">✦</span>
                            <div>
                                <h3 className="settings__about-name">{APP_INFO.name}</h3>
                                <span className="settings__about-tagline">{APP_INFO.tagline}</span>
                            </div>
                        </div>

                        <div className="settings__about-details">
                            <div className="settings__about-item">
                                <span className="settings__about-key">Version</span>
                                <span className="settings__about-val">{APP_INFO.version}</span>
                            </div>
                            <div className="settings__about-item">
                                <span className="settings__about-key">Department</span>
                                <span className="settings__about-val">{APP_INFO.department}</span>
                            </div>
                            <div className="settings__about-item">
                                <span className="settings__about-key">Academic Year</span>
                                <span className="settings__about-val">{APP_INFO.year} · {APP_INFO.semester}</span>
                            </div>

                        </div>

                        <div className="settings__about-desc">
                            <p>
                                <strong>{APP_INFO.name}</strong> is an AI-powered study companion that
                                helps university students prepare for exams using intelligent tutoring,
                                RAG-based syllabus retrieval, and adaptive study planning.
                            </p>
                        </div>



                        <div className="settings__about-footer">
                            <span>Built with ❤️ for students</span>
                            <span className="settings__about-version">v{APP_INFO.version}</span>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}

export default Settings;
