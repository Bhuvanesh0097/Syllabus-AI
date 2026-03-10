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

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
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

function StudyPlan({ onBack, studentInfo, persistedState, onStateChange }) {
    // ── Persistent state (survives page switches via App.jsx) ──
    const selectedSubject = persistedState.selectedSubject;
    const section = persistedState.section ?? (studentInfo?.section || 'A');
    const message = persistedState.message;
    const plan = persistedState.plan;
    const refineMessages = persistedState.refineMessages;

    // Helpers to update persisted state
    const updateState = useCallback((updates) => {
        onStateChange(prev => ({ ...prev, ...updates }));
    }, [onStateChange]);

    const setSelectedSubject = useCallback((v) => updateState({ selectedSubject: v }), [updateState]);
    const setSection = useCallback((v) => updateState({ section: v }), [updateState]);
    const setMessage = useCallback((v) => updateState({ message: v }), [updateState]);
    const setPlan = useCallback((v) => updateState({ plan: v }), [updateState]);
    const setRefineMessages = useCallback((v) => {
        // Support both direct value and updater function
        if (typeof v === 'function') {
            onStateChange(prev => ({ ...prev, refineMessages: v(prev.refineMessages) }));
        } else {
            updateState({ refineMessages: v });
        }
    }, [onStateChange, updateState]);

    // ── Transient state (resets on page switch — that's fine) ──
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [refineInput, setRefineInput] = useState('');
    const [refineLoading, setRefineLoading] = useState(false);
    const [refineError, setRefineError] = useState(null);
    const textareaRef = useRef(null);
    const refineInputRef = useRef(null);
    const refineEndRef = useRef(null);

    // Auto-focus the textarea
    useEffect(() => {
        if (!plan && textareaRef.current) {
            textareaRef.current.focus();
        }
    }, [plan]);

    // Auto-scroll refinement messages
    useEffect(() => {
        refineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [refineMessages, refineLoading]);

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
            setRefineMessages([]);
            setRefineError(null);
        } catch (err) {
            console.error('Plan generation failed:', err);
            setError(err.message || 'Failed to generate study plan');
        } finally {
            setLoading(false);
        }
    }, [selectedSubject, section, message, setPlan, setRefineMessages]);

    // Handle Enter key (Shift+Enter for newline)
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleGenerate();
        }
    };

    // ── Refine Plan ──
    const handleRefine = useCallback(async () => {
        if (!refineInput.trim() || refineLoading || !plan) return;

        const userMsg = refineInput.trim();
        setRefineInput('');
        setRefineError(null);

        // Add user message to chat
        setRefineMessages(prev => [...prev, { role: 'user', content: userMsg }]);

        setRefineLoading(true);

        try {
            const result = await api.refineStudyPlan({
                subject_code: plan.subject_code || selectedSubject,
                current_plan: plan.plan_markdown,
                modification_request: userMsg,
                section: section,
            });

            // Update the plan with the refined version
            setPlan(result.plan);

            // Add AI response to chat
            setRefineMessages(prev => [...prev, {
                role: 'assistant',
                content: '✅ Plan updated based on your request.',
            }]);
        } catch (err) {
            console.error('Plan refinement failed:', err);
            setRefineError(err.message || 'Failed to refine study plan');
            setRefineMessages(prev => [...prev, {
                role: 'assistant',
                content: `⚠️ Sorry, I couldn't update the plan: ${err.message}`,
                isError: true,
            }]);
        } finally {
            setRefineLoading(false);
        }
    }, [refineInput, refineLoading, plan, selectedSubject, section, setPlan, setRefineMessages]);

    // Handle Enter key in refine input
    const handleRefineKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleRefine();
        }
    };

    // ── Download state ──
    const [showDownloadMenu, setShowDownloadMenu] = useState(false);
    const downloadMenuRef = useRef(null);

    // Close download menu when clicking outside
    useEffect(() => {
        if (!showDownloadMenu) return;
        const handleClickOutside = (e) => {
            if (downloadMenuRef.current && !downloadMenuRef.current.contains(e.target)) {
                setShowDownloadMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [showDownloadMenu]);

    // ── Download as Markdown (.md) ──
    const downloadAsMarkdown = useCallback(() => {
        if (!plan) return;
        const subjectName = (plan.subject_name || 'Study').replace(/\s+/g, '_');
        const filename = `${subjectName}_Study_Plan.md`;
        const blob = new Blob([plan.plan_markdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        setShowDownloadMenu(false);
    }, [plan]);

    // ── Download as PDF (styled print window) ──
    const downloadAsPdf = useCallback(() => {
        if (!plan) return;
        setShowDownloadMenu(false);

        // Convert markdown to basic HTML
        let html = plan.plan_markdown;
        html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background:#1a1a2e;padding:12px 16px;border-radius:8px;overflow-x:auto;font-size:13px;color:#e2e8f0"><code>$2</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code style="background:#edf2f7;padding:1px 5px;border-radius:3px;font-size:0.9em">$1</code>');
        html = html.replace(/^#### (.+)$/gm, '<h4 style="margin:16px 0 8px;font-size:14px;color:#4a5568">$1</h4>');
        html = html.replace(/^### (.+)$/gm, '<h3 style="margin:20px 0 10px;font-size:16px;color:#2d3748;border-bottom:1px solid #e2e8f0;padding-bottom:6px">$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2 style="margin:24px 0 12px;font-size:20px;color:#1a202c">$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1 style="margin:28px 0 14px;font-size:24px;color:#1a202c">$1</h1>');
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/^&gt; (.+)$/gm, '<blockquote style="border-left:3px solid #6c63ff;padding-left:12px;margin:8px 0;color:#4a5568;font-style:italic">$1</blockquote>');
        html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0"/>');
        html = html.replace(/^[\-\*] (.+)$/gm, '<li style="margin:4px 0">$1</li>');
        html = html.replace(/((?:<li style="margin:4px 0">.*<\/li>\n?)+)/g, '<ul style="padding-left:20px;margin:8px 0">$1</ul>');
        html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin:4px 0">$1</li>');
        // Wrap standalone text lines in paragraphs
        html = html.replace(/^(?!<[a-z])(.*\S.*)$/gm, (match) => {
            if (/^</.test(match)) return match;
            return `<p style="margin:6px 0;line-height:1.6">${match}</p>`;
        });

        const subjectName = plan.subject_name || 'Study Plan';
        const printHtml = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>${subjectName} - Study Plan</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', -apple-system, system-ui, sans-serif; color: #1a202c; padding: 40px 48px; max-width: 800px; margin: 0 auto; line-height: 1.6; }
  .header { text-align: center; margin-bottom: 32px; padding-bottom: 20px; border-bottom: 2px solid #6c63ff; }
  .header h1 { font-size: 22px; font-weight: 800; color: #1a202c; margin-bottom: 4px; }
  .header p { font-size: 12px; color: #718096; }
  .badge { display: inline-block; padding: 2px 10px; background: #ebf4ff; border-radius: 12px; font-size: 11px; font-weight: 600; color: #4c51bf; margin: 4px; }
  .content { font-size: 14px; }
  strong { color: #2d3748; }
  @media print { body { padding: 20px 24px; } .header { margin-bottom: 20px; } }
</style></head><body>
  <div class="header">
    <h1>📋 ${subjectName} — Study Plan</h1>

    ${plan.days_available > 0 ? `<span class="badge">📅 ${plan.days_available} ${plan.days_available === 1 ? 'Session' : 'Days'}</span>` : ''}

  </div>
  <div class="content">${html}</div>
</body></html>`;

        const printWindow = window.open('', '_blank', 'width=800,height=900');
        printWindow.document.write(printHtml);
        printWindow.document.close();
        // Give fonts a moment to load, then trigger print
        setTimeout(() => printWindow.print(), 600);
    }, [plan, section]);

    // ═══════════════════════════════════════════════════════
    // RESULT VIEW
    // ═══════════════════════════════════════════════════════
    if (plan) {
        const subject = SUBJECTS[plan.subject_code] || {};
        return (
            <div className="sp sp--result animate-fade-in">
                {/* Header */}
                <div className="sp__header">
                    <button className="btn btn-ghost" onClick={() => { setPlan(null); setRefineMessages([]); }}>
                        ← New Plan
                    </button>
                    <div className="sp__header-info">
                        <span className="sp__header-icon">📋</span>
                        <div>
                            <h1 className="sp__header-title">
                                {subject.icon} {plan.subject_name || 'Study'} Plan
                            </h1>

                        </div>
                    </div>

                    {/* Download Button */}
                    <div className="sp__download-wrap">
                        <button
                            className="sp__download-btn"
                            onClick={() => setShowDownloadMenu(prev => !prev)}
                            title="Download study plan"
                        >
                            📥 Download
                        </button>
                        {showDownloadMenu && (
                            <div className="sp__download-menu animate-fade-in">
                                <button className="sp__download-option" onClick={downloadAsMarkdown}>
                                    <span className="sp__download-option-icon">📄</span>
                                    <div>
                                        <span className="sp__download-option-title">Markdown (.md)</span>
                                        <span className="sp__download-option-desc">Plain text, editable</span>
                                    </div>
                                </button>
                                <button className="sp__download-option" onClick={downloadAsPdf}>
                                    <span className="sp__download-option-icon">📑</span>
                                    <div>
                                        <span className="sp__download-option-title">PDF (Print)</span>
                                        <span className="sp__download-option-desc">Professional, styled</span>
                                    </div>
                                </button>
                            </div>
                        )}
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
                        isLast={refineMessages.length === 0}
                    />
                </div>

                {/* ── Refinement Chat Area ── */}
                <div className="sp__refine-section">
                    <div className="sp__refine-divider">
                        <span className="sp__refine-divider-line" />
                        <span className="sp__refine-divider-text">✏️ Modify this plan</span>
                        <span className="sp__refine-divider-line" />
                    </div>

                    {/* Refinement Messages */}
                    {refineMessages.length > 0 && (
                        <div className="sp__refine-messages">
                            {refineMessages.map((msg, i) => (
                                <div key={i} className={`sp__refine-msg sp__refine-msg--${msg.role} ${msg.isError ? 'sp__refine-msg--error' : ''}`}>
                                    <span className="sp__refine-msg-avatar">
                                        {msg.role === 'user' ? '👤' : '✦'}
                                    </span>
                                    <span className="sp__refine-msg-text">{msg.content}</span>
                                </div>
                            ))}
                            {refineLoading && (
                                <div className="sp__refine-msg sp__refine-msg--assistant animate-fade-in">
                                    <span className="sp__refine-msg-avatar">✦</span>
                                    <span className="sp__refine-msg-text">
                                        <span className="sp__refine-typing">
                                            <span /><span /><span />
                                        </span>
                                        Updating your plan...
                                    </span>
                                </div>
                            )}
                            <div ref={refineEndRef} />
                        </div>
                    )}

                    {/* Refine Error */}
                    {refineError && (
                        <div className="sp__error">
                            <span>⚠️</span> {refineError}
                        </div>
                    )}

                    {/* Refine Input */}
                    <div className="sp__refine-input-area">
                        <div className="sp__refine-input-wrap">
                            <input
                                ref={refineInputRef}
                                type="text"
                                className="sp__refine-input"
                                placeholder="e.g. &quot;Make it 3 days instead&quot;, &quot;Add more time for Unit 2&quot;, &quot;Remove revision day&quot;..."
                                value={refineInput}
                                onChange={(e) => setRefineInput(e.target.value)}
                                onKeyDown={handleRefineKeyDown}
                                disabled={refineLoading}
                            />
                            <button
                                className="sp__refine-send"
                                onClick={handleRefine}
                                disabled={!refineInput.trim() || refineLoading}
                                title="Send modification request"
                            >
                                {refineLoading ? (
                                    <span className="sp__spinner-sm" />
                                ) : (
                                    '↑'
                                )}
                            </button>
                        </div>
                        <span className="sp__refine-hint">
                            Press <kbd>Enter</kbd> to modify · The AI will regenerate your plan with changes
                        </span>
                    </div>
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
