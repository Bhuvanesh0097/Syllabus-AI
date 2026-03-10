/**
 * ChatInput Component — message input bar with smart style selector
 * and quick-action suggestion chips for common interaction patterns.
 */

import { useState, useCallback } from 'react';
import './ChatInput.css';

// Quick-action chips that students can click to set a style context
const QUICK_ACTIONS = [
    { label: 'Explain Simply', prefix: 'Explain simply: ', icon: '💡' },
    { label: 'Make it Brief', prefix: 'Make it brief: ', icon: '⚡' },
    { label: 'Detailed Answer', prefix: 'Give a detailed answer: ', icon: '📖' },
    { label: 'Summarize', prefix: 'Summarize: ', icon: '📋' },
    { label: 'Step by Step', prefix: 'Break it down step by step: ', icon: '🔢' },
    { label: 'Exam Format', prefix: 'Give an exam-ready answer: ', icon: '🎯' },
];

function ChatInput({ onSend, isLoading, subjectCode }) {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!message.trim() || isLoading) return;
        onSend(message);
        setMessage('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleQuickAction = useCallback((action) => {
        // If there's already text, prepend the style prefix
        // If no text, just set the prefix so student can type the topic
        if (message.trim()) {
            const combined = `${action.prefix}${message.trim()}`;
            onSend(combined);
            setMessage('');
        } else {
            setMessage(action.prefix);
            // Focus the textarea
            const textarea = document.querySelector('.chat-input__textarea');
            if (textarea) {
                textarea.focus();
                // Place cursor at end
                setTimeout(() => {
                    textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
                }, 0);
            }
        }
    }, [message, onSend]);



    return (
        <div className="chat-input-container">
            {/* ── Quick Action Chips ── */}
            <div className="chat-input__quick-actions">
                {QUICK_ACTIONS.map((action) => (
                    <button
                        key={action.label}
                        type="button"
                        className="chat-input__quick-chip"
                        onClick={() => handleQuickAction(action)}
                        disabled={isLoading}
                        title={`Click to ask with "${action.label}" style`}
                    >
                        <span className="chat-input__chip-icon">{action.icon}</span>
                        <span>{action.label}</span>
                    </button>
                ))}
            </div>

            <form className="chat-input" onSubmit={handleSubmit}>


                {/* ── Text Input ── */}
                <textarea
                    className="chat-input__textarea"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={subjectCode
                        ? `Ask about ${subjectCode}... Try "explain simply" or "make it brief"`
                        : "Ask anything... Try natural phrases like \"summarize\" or \"break it down\""
                    }
                    rows={1}
                    disabled={isLoading}
                />

                {/* ── Send Button ── */}
                <button
                    type="submit"
                    className={`chat-input__send ${message.trim() ? 'chat-input__send--active' : ''}`}
                    disabled={!message.trim() || isLoading}
                >
                    {isLoading ? (
                        <span className="chat-input__loading">
                            <span className="chat-input__dot" />
                            <span className="chat-input__dot" />
                            <span className="chat-input__dot" />
                        </span>
                    ) : (
                        <span>↑</span>
                    )}
                </button>
            </form>

            <p className="chat-input__disclaimer">
                AI adapts to your style — say "explain simply", "make it brief", or "give detailed answer" naturally.
            </p>
        </div>
    );
}

export default ChatInput;
