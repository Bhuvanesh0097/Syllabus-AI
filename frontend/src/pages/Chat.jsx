/**
 * Chat Page — ChatGPT-style AI conversation interface.
 * Auto-triggers a personalized greeting on session start.
 * Supports smart subject/unit switching and new chat creation.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import UnitSelector from '../components/UnitSelector';
import { SUBJECTS } from '../utils/constants';
import './Chat.css';

const UNITS_LIST = [1, 2, 3, 4, 5];

function Chat({ subjectCode: initialSubjectCode, initialUnit, studentInfo, onBack, onSwitchContext, tone, chatState }) {
    const [selectedUnit, setSelectedUnit] = useState(initialUnit || null);
    const [activeSubject, setActiveSubject] = useState(initialSubjectCode);
    const [showNewChatPanel, setShowNewChatPanel] = useState(false);
    const [newChatSubject, setNewChatSubject] = useState('');
    const [newChatUnit, setNewChatUnit] = useState('');
    const [showScrollBtn, setShowScrollBtn] = useState(false);

    // Use chat state lifted from App.jsx so it persists across page switches
    const {
        messages,
        isLoading,
        chatId,
        error,
        sessionStarted,
        lastContextSwitch,
        startSession,
        sendMessage,
        clearChat,
    } = chatState;
    const messagesEndRef = useRef(null);
    const messagesContainerRef = useRef(null);
    const subject = SUBJECTS[activeSubject];

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Track scroll position to show/hide the scroll-to-bottom button
    useEffect(() => {
        const container = messagesContainerRef.current;
        if (!container) return;

        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            // Show button when scrolled up more than 150px from the bottom
            const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
            setShowScrollBtn(!isNearBottom);
        };

        container.addEventListener('scroll', handleScroll, { passive: true });
        return () => container.removeEventListener('scroll', handleScroll);
    }, []);

    // Scroll to the latest message
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    // ── Auto-trigger AI greeting when unit is selected ──
    useEffect(() => {
        if (selectedUnit && !sessionStarted && studentInfo) {
            startSession({
                name: studentInfo.name,
                subject: activeSubject,
                unit: selectedUnit,
                section: studentInfo.section,
                department: studentInfo.department,
                year: studentInfo.year,
                semester: studentInfo.semester,
            });
        }
    }, [selectedUnit, sessionStarted, studentInfo, activeSubject, startSession]);

    // ── React to context switches detected by the backend ──
    useEffect(() => {
        if (lastContextSwitch) {
            if (lastContextSwitch.subject_code) {
                setActiveSubject(lastContextSwitch.subject_code);
            }
            if (lastContextSwitch.unit_number) {
                setSelectedUnit(lastContextSwitch.unit_number);
            }
            // Notify parent (App.jsx) about the context change
            if (onSwitchContext) {
                onSwitchContext({
                    subjectCode: lastContextSwitch.subject_code,
                    unitNumber: lastContextSwitch.unit_number,
                });
            }
        }
    }, [lastContextSwitch, onSwitchContext]);

    const handleSend = useCallback(
        (content, options) => {
            sendMessage(content, {
                ...options,
                subjectCode: activeSubject,
                unitNumber: selectedUnit,
                section: studentInfo?.section,
                tone,
            });
        },
        [sendMessage, activeSubject, selectedUnit, studentInfo, tone]
    );

    // ── New Chat Panel Logic ──
    const handleNewChatOpen = useCallback(() => {
        setNewChatSubject(activeSubject || '');
        setNewChatUnit('');
        setShowNewChatPanel(true);
    }, [activeSubject]);

    const handleNewChatStart = useCallback(() => {
        if (!newChatSubject || !newChatUnit) return;
        clearChat();
        setActiveSubject(newChatSubject);
        setSelectedUnit(parseInt(newChatUnit));
        setShowNewChatPanel(false);
    }, [newChatSubject, newChatUnit, clearChat]);

    const handleNewChatCancel = useCallback(() => {
        setShowNewChatPanel(false);
    }, []);

    const handleChangeUnit = useCallback(() => {
        clearChat();
        setSelectedUnit(null);
    }, [clearChat]);

    // Show unit selector if no unit selected
    if (!selectedUnit) {
        return (
            <UnitSelector
                subjectCode={activeSubject}
                selectedUnit={selectedUnit}
                onSelect={setSelectedUnit}
                onBack={onBack}
            />
        );
    }

    return (
        <div className="chat-page">
            {/* ── Header ── */}
            <header className="chat-page__header">
                <div className="chat-page__header-left">
                    <button className="btn btn-ghost" onClick={handleChangeUnit}>
                        ← Units
                    </button>
                    <div className="chat-page__subject-info">
                        <span className="chat-page__subject-icon">{subject?.icon}</span>
                        <div>
                            <span className="chat-page__subject-name">{subject?.shortName}</span>
                            <span className="chat-page__unit-badge badge badge-accent">
                                Unit {selectedUnit}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="chat-page__header-right">
                    {studentInfo && (
                        <span className="chat-page__student-name">
                            👤 {studentInfo.name}
                            <span className="chat-page__student-section">
                                · Sec {studentInfo.section}
                            </span>
                        </span>
                    )}
                    <button className="btn btn-ghost btn-sm" onClick={handleNewChatOpen}>
                        + New Chat
                    </button>
                </div>
            </header>

            {/* ── New Chat Panel (overlay) ── */}
            {showNewChatPanel && (
                <div className="chat-page__new-chat-overlay animate-fade-in">
                    <div className="chat-page__new-chat-panel glass-strong">
                        <h3 className="chat-page__new-chat-title">🆕 Start a New Chat</h3>
                        <p className="chat-page__new-chat-desc">
                            Select a subject and unit to begin a fresh conversation.
                        </p>

                        {/* Subject Selection */}
                        <div className="chat-page__new-chat-field">
                            <label>Subject</label>
                            <div className="chat-page__new-chat-subjects">
                                {Object.values(SUBJECTS).map((s) => (
                                    <button
                                        key={s.code}
                                        type="button"
                                        className={`chat-page__new-chat-chip ${newChatSubject === s.code ? 'chat-page__new-chat-chip--active' : ''}`}
                                        style={{ '--chip-color': s.color }}
                                        onClick={() => setNewChatSubject(s.code)}
                                    >
                                        <span>{s.icon}</span>
                                        <span>{s.code}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Unit Selection */}
                        <div className="chat-page__new-chat-field">
                            <label>Unit</label>
                            <div className="chat-page__new-chat-units">
                                {UNITS_LIST.map((u) => (
                                    <button
                                        key={u}
                                        type="button"
                                        className={`chat-page__new-chat-unit-btn ${newChatUnit == u ? 'chat-page__new-chat-unit-btn--active' : ''}`}
                                        onClick={() => setNewChatUnit(u)}
                                    >
                                        Unit {u}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="chat-page__new-chat-actions">
                            <button className="btn btn-ghost" onClick={handleNewChatCancel}>
                                Cancel
                            </button>
                            <button
                                className={`chat-page__new-chat-start ${newChatSubject && newChatUnit ? 'chat-page__new-chat-start--ready' : ''}`}
                                disabled={!newChatSubject || !newChatUnit}
                                onClick={handleNewChatStart}
                            >
                                Start Chat →
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Context Switch Notification ── */}
            {lastContextSwitch && (
                <div className="chat-page__switch-notice animate-fade-in">
                    <span className="chat-page__switch-icon">🔄</span>
                    <span>
                        Switched to <strong>{SUBJECTS[lastContextSwitch.subject_code]?.shortName || lastContextSwitch.subject_code}</strong>
                        {lastContextSwitch.unit_number && <> — Unit {lastContextSwitch.unit_number}</>}
                    </span>
                </div>
            )}

            {/* ── Messages ── */}
            <div className="chat-page__messages" ref={messagesContainerRef}>
                {/* Loading state for greeting generation */}
                {messages.length === 0 && isLoading && (
                    <div className="chat-page__greeting-loading animate-fade-in">
                        <div className="chat-page__greeting-loader">
                            <div className="chat-page__greeting-spinner" />
                            <h3>Preparing your study session...</h3>
                            <p>
                                Generating a personalized overview for{' '}
                                <strong>{subject?.name}</strong> — Unit {selectedUnit}
                            </p>
                        </div>
                    </div>
                )}

                {/* No-messages empty state only if session started and not loading */}
                {messages.length === 0 && !isLoading && sessionStarted && (
                    <div className="chat-page__empty animate-fade-in">
                        <div className="chat-page__empty-icon">✦</div>
                        <h2>Ready to Study</h2>
                        <p>
                            Ask me anything about{' '}
                            <strong>{subject?.name}</strong> — Unit {selectedUnit}
                        </p>
                    </div>
                )}

                {/* Render messages */}
                {messages.map((msg, i) => (
                    <ChatMessage
                        key={`${msg.role}-${i}`}
                        message={msg}
                        isLast={i === messages.length - 1}
                    />
                ))}

                {/* Typing indicator for follow-up messages */}
                {isLoading && messages.length > 0 && (
                    <div className="chat-page__typing animate-fade-in">
                        <div className="chat-page__typing-avatar">✦</div>
                        <div className="chat-page__typing-dots">
                            <span />
                            <span />
                            <span />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* ── Scroll to Bottom Button ── */}
            {showScrollBtn && (
                <button
                    className="chat-page__scroll-bottom"
                    onClick={scrollToBottom}
                    aria-label="Scroll to latest message"
                    title="Jump to latest message"
                >
                    ↓
                </button>
            )}

            {/* ── Input ── */}
            <div className="chat-page__input-area">
                <ChatInput
                    onSend={handleSend}
                    isLoading={isLoading}
                    subjectCode={activeSubject}
                />
            </div>
        </div>
    );
}

export default Chat;
