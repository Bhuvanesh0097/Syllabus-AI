/**
 * StudyPlan Page — Chatbox-first AI study planner.
 *
 * Architecture:
 *   User Chatbox + Subject/Section selectors
 *       ↓
 *   AI Study Planner Prompt (RAG-powered)
 *       ↓
 *   Structured Plan Output (⏱ Timeline · 📚 Topics · ✅ Checklist)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { SUBJECTS } from '../utils/constants';
import ChatMessage from '../components/ChatMessage';
import api from '../api/client';
import './StudyPlan.css';

const SECTIONS = ['A', 'B', 'C'];

const QUICK_PROMPTS = [
    { label: '📖 Full Prep', text: 'Create a full preparation study plan for all 5 units, 2 hours per day' },
    { label: '⚡ Quick Review', text: 'Quick revision plan for all units in 2 hours' },
    { label: '🌙 Night Before', text: 'Emergency last-minute cramming plan, 3 hours, cover most important topics only' },
    { label: '📝 Exam Focused', text: 'Create an exam-focused plan for units 1-3, 4 hours per day, 3 days before exam' },
];

function StudyPlan({ onBack, studentInfo }) {
    // ── State ──
    const [selectedSubject, setSelectedSubject] = useState(null);
    const [section, setSection] = useState(studentInfo?.section || 'A');
    const [message, setMessage] = useState('');
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const textareaRef = useRef(null);

    // Auto-focus the textarea
    useEffect(() => {
        if (!plan && textareaRef.current) {
            textareaRef.current.focus();
        }
    }, [plan]);

    // Auto-resize textarea
    const handleTextareaChange = (e) => {
        setMessage(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
    };

    // ── Quick prompt click ──
    const handleQuickPrompt = (text) => {
        setMessage(text);
        if (textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
        }
    };

    // ── Generate ──
    const handleGenerate = useCallback(async () => {
        if (!selectedSubject) {
            setError('Please select a subject first');
            return;
        }
        if (!message.trim()) {
            setError('Please describe what kind of study plan you need');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const result = await api.generateStudyPlan({
                subject_code: selectedSubject,
                section: section,
                custom_request: message.trim(),
            });
            setPlan(result.plan);
        } catch (err) {
            console.error('Plan generation failed:', err);
            setError(err.message || 'Failed to generate study plan');
        } finally {
            setLoading(false);
        }
    }, [selectedSubject, section, message]);

    // Handle Enter key (Shift+Enter for newline)
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleGenerate();
        }
    };

    // ═══════════════════════════════════════════════════════
    // RESULT VIEW
    // ═══════════════════════════════════════════════════════
    if (plan) {
        const subject = SUBJECTS[plan.subject_code] || {};
        return (
            <div className="sp animate-fade-in">
                {/* Header */}
                <div className="sp__header">
                    <button className="btn btn-ghost" onClick={() => setPlan(null)}>
                        ← New Plan
                    </button>
                    <div className="sp__header-info">
                        <span className="sp__header-icon">📋</span>
                        <div>
                            <h1 className="sp__header-title">
                                {subject.icon} {plan.subject_name || 'Study'} Plan
                            </h1>
                            <p className="sp__header-sub">
                                AI-generated · Section {section}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Stats Strip */}
                <div className="sp__stats">
                    {plan.days_available > 0 && (
                        <div className="sp__stat">
                            <span className="sp__stat-icon">📅</span>
                            <span className="sp__stat-val">{plan.days_available}</span>
                            <span className="sp__stat-lbl">{plan.days_available === 1 ? 'Session' : 'Days'}</span>
                        </div>
                    )}
                    {plan.topics_retrieved && (
                        <div className="sp__stat sp__stat--rag">
                            <span className="sp__stat-icon">✅</span>
                            <span className="sp__stat-val">RAG</span>
                            <span className="sp__stat-lbl">Syllabus</span>
                        </div>
                    )}
                </div>

                {/* Your Request */}
                <div className="sp__user-request">
                    <span className="sp__user-request-label">Your request:</span>
                    <span className="sp__user-request-text">{message}</span>
                </div>

                {/* Plan Content */}
                <div className="sp__plan-content">
                    <ChatMessage
                        message={{
                            role: 'assistant',
                            content: plan.plan_markdown,
                            timestamp: new Date().toISOString(),
                        }}
                        isLast={true}
                    />
                </div>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════
    // INPUT VIEW — Chatbox-first
    // ═══════════════════════════════════════════════════════
    return (
        <div className="sp animate-fade-in">
            {/* Header */}
            <div className="sp__header">
                <button className="btn btn-ghost" onClick={onBack}>← Back</button>
                <div className="sp__header-info">
                    <span className="sp__header-icon">📋</span>
                    <div>
                        <h1 className="sp__header-title">Study Plan Builder</h1>
                        <p className="sp__header-sub">
                            Tell the AI what you need — it builds your exam schedule
                        </p>
                    </div>
                </div>
            </div>

            {/* Subject + Section Toolbar */}
            <div className="sp__toolbar">
                <div className="sp__toolbar-group">
                    <span className="sp__toolbar-label">Subject</span>
                    <div className="sp__subject-pills">
                        {Object.values(SUBJECTS).map((subj) => (
                            <button
                                key={subj.code}
                                className={`sp__pill ${selectedSubject === subj.code ? 'sp__pill--active' : ''}`}
                                style={{ '--pill-color': subj.color }}
                                onClick={() => setSelectedSubject(subj.code)}
                            >
                                <span>{subj.icon}</span>
                                <span>{subj.code}</span>
                            </button>
                        ))}
                    </div>
                </div>
                <div className="sp__toolbar-group">
                    <span className="sp__toolbar-label">Section</span>
                    <div className="sp__section-pills">
                        {SECTIONS.map((s) => (
                            <button
                                key={s}
                                className={`sp__sec-pill ${section === s ? 'sp__sec-pill--active' : ''}`}
                                onClick={() => setSection(s)}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Quick Prompts */}
            <div className="sp__quick-prompts">
                {QUICK_PROMPTS.map((qp, i) => (
                    <button
                        key={i}
                        className="sp__quick-btn"
                        onClick={() => handleQuickPrompt(qp.text)}
                    >
                        {qp.label}
                    </button>
                ))}
            </div>

            {/* Main Chatbox */}
            <div className="sp__chatbox">
                <textarea
                    ref={textareaRef}
                    className="sp__chatbox-input"
                    placeholder={selectedSubject
                        ? `Describe your study plan needs for ${SUBJECTS[selectedSubject]?.shortName}...\n\nExamples:\n• "Create a plan for units 1-3, 2 hours per day, 5 days"\n• "Quick revision for unit 4, 1 hour total"\n• "Full preparation for all units, focus on important exam topics"`
                        : 'First select a subject above, then describe your study plan needs...'}
                    value={message}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    rows={4}
                    disabled={loading}
                />

                {/* Error */}
                {error && (
                    <div className="sp__error">
                        <span>⚠️</span> {error}
                    </div>
                )}

                {/* Generate */}
                <div className="sp__chatbox-footer">
                    <span className="sp__chatbox-hint">
                        Press <kbd>Enter</kbd> to generate · <kbd>Shift+Enter</kbd> for new line
                    </span>
                    <button
                        className="sp__generate-btn"
                        onClick={handleGenerate}
                        disabled={loading || !selectedSubject || !message.trim()}
                    >
                        {loading ? (
                            <>
                                <span className="sp__spinner" />
                                Generating...
                            </>
                        ) : (
                            '🚀 Generate Plan'
                        )}
                    </button>
                </div>
            </div>

            {/* Loading State */}
            {loading && (
                <div className="sp__loading-state">
                    <div className="sp__loading-steps">
                        <div className="sp__loading-step sp__loading-step--done">
                            ✅ Retrieving syllabus topics from PDFs...
                        </div>
                        <div className="sp__loading-step sp__loading-step--active">
                            <span className="sp__spinner-sm" />
                            Building your study schedule...
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default StudyPlan;
