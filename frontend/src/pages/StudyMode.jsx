/**
 * StudyMode Page — 2-Mark and 10-Mark exam preparation modes.
 * Displays clickable question lists; generates AI answers on demand.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import ChatMessage from '../components/ChatMessage';
import api from '../api/client';
import { SUBJECTS } from '../utils/constants';
import './StudyMode.css';

function StudyMode({ subjectCode, studentInfo, onBack }) {
    // ── State ──
    const [selectedUnit, setSelectedUnit] = useState(null);
    const [selectedMode, setSelectedMode] = useState(null); // '2_mark' | '10_mark'
    const [questions, setQuestions] = useState([]);
    const [loadingQuestions, setLoadingQuestions] = useState(false);
    const [activeQuestion, setActiveQuestion] = useState(null); // question being answered
    const [answer, setAnswer] = useState(null);
    const [loadingAnswer, setLoadingAnswer] = useState(false);
    const [error, setError] = useState(null);
    const [unitTitle, setUnitTitle] = useState('');
    const answerRef = useRef(null);

    const subject = SUBJECTS[subjectCode];
    const studentSection = studentInfo?.section || null;

    // Auto-scroll to answer when it loads
    useEffect(() => {
        if (answer && answerRef.current) {
            answerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [answer]);

    // ── Fetch Questions ──
    const fetchQuestions = useCallback(async (unit, mode) => {
        setLoadingQuestions(true);
        setError(null);
        setQuestions([]);
        setAnswer(null);
        setActiveQuestion(null);

        try {
            const response = await api.getStudyQuestions(subjectCode, unit, mode, studentSection);
            setQuestions(response.questions || []);
            setUnitTitle(response.unit_title || `Unit ${unit}`);
        } catch (err) {
            console.error('Failed to fetch questions:', err);
            setError(err.message);
        } finally {
            setLoadingQuestions(false);
        }
    }, [subjectCode, studentSection]);

    // ── Fetch Answer for a Question ──
    const fetchAnswer = useCallback(async (question) => {
        if (loadingAnswer) return;

        setActiveQuestion(question);
        setAnswer(null);
        setLoadingAnswer(true);

        try {
            const response = await api.getQuestionAnswer(
                subjectCode,
                selectedUnit,
                selectedMode,
                question,
                studentSection
            );
            setAnswer(response.answer || 'No answer generated.');
        } catch (err) {
            console.error('Failed to fetch answer:', err);
            setAnswer(`⚠️ Error: ${err.message}`);
        } finally {
            setLoadingAnswer(false);
        }
    }, [subjectCode, selectedUnit, selectedMode, loadingAnswer, studentSection]);

    // ── Handlers ──
    const handleSelectMode = (mode) => {
        setSelectedMode(mode);
        if (selectedUnit) {
            fetchQuestions(selectedUnit, mode);
        }
    };

    const handleSelectUnit = (unit) => {
        setSelectedUnit(unit);
        if (selectedMode) {
            fetchQuestions(unit, selectedMode);
        }
    };

    const handleReset = () => {
        setSelectedUnit(null);
        setSelectedMode(null);
        setQuestions([]);
        setAnswer(null);
        setActiveQuestion(null);
        setError(null);
    };

    const handleChangeMode = () => {
        setSelectedMode(null);
        setQuestions([]);
        setAnswer(null);
        setActiveQuestion(null);
    };

    const modeLabel = selectedMode === '2_mark' ? '2 Mark' : '10 Mark';
    const modeIcon = selectedMode === '2_mark' ? '📝' : '📖';

    // ═══════════════════════════════════════════════════════════
    // STEP 1: Mode Selection
    // ═══════════════════════════════════════════════════════════
    if (!selectedMode) {
        return (
            <div className="study-mode animate-fade-in">
                <div className="study-mode__header">
                    <div className="study-mode__title-group">
                        <span className="study-mode__icon">{subject?.icon}</span>
                        <div>
                            <h1 className="study-mode__title">Study Mode</h1>
                            <p className="study-mode__subtitle">{subject?.name}</p>
                        </div>
                    </div>
                </div>

                <div className="study-mode__mode-select">
                    <h2 className="study-mode__section-title">
                        Choose Preparation Mode
                    </h2>
                    <p className="study-mode__section-desc">
                        Select the type of questions you want to practice
                    </p>

                    <div className="study-mode__mode-cards">
                        <button
                            className="study-mode__mode-card card card-interactive"
                            onClick={() => handleSelectMode('2_mark')}
                        >
                            <div className="study-mode__mode-icon-wrap study-mode__mode-icon--2mark">
                                <span>📝</span>
                            </div>
                            <h3>2 Mark Questions</h3>
                            <p>
                                Short, definition-based questions. Quick recall practice
                                for concise, exam-ready answers.
                            </p>
                            <div className="study-mode__mode-tags">
                                <span className="badge">Define</span>
                                <span className="badge">What is</span>
                                <span className="badge">State</span>
                                <span className="badge">List</span>
                            </div>
                            <span className="study-mode__mode-action">
                                Start Practicing →
                            </span>
                        </button>

                        <button
                            className="study-mode__mode-card card card-interactive"
                            onClick={() => handleSelectMode('10_mark')}
                        >
                            <div className="study-mode__mode-icon-wrap study-mode__mode-icon--10mark">
                                <span>📖</span>
                            </div>
                            <h3>10 Mark Questions</h3>
                            <p>
                                Detailed, structured questions requiring in-depth
                                explanations with examples and diagrams.
                            </p>
                            <div className="study-mode__mode-tags">
                                <span className="badge">Explain</span>
                                <span className="badge">Describe</span>
                                <span className="badge">Compare</span>
                                <span className="badge">Discuss</span>
                            </div>
                            <span className="study-mode__mode-action">
                                Start Practicing →
                            </span>
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 2: Unit Selection (if mode selected but no unit)
    // ═══════════════════════════════════════════════════════════
    if (!selectedUnit) {
        return (
            <div className="study-mode animate-fade-in">
                <div className="study-mode__header">
                    <button className="btn btn-ghost" onClick={handleChangeMode}>← Modes</button>
                    <div className="study-mode__title-group">
                        <span className="study-mode__icon">{modeIcon}</span>
                        <div>
                            <h1 className="study-mode__title">{modeLabel} Questions</h1>
                            <p className="study-mode__subtitle">{subject?.name}</p>
                        </div>
                    </div>
                </div>

                <div className="study-mode__unit-select">
                    <h2 className="study-mode__section-title">Select a Unit</h2>
                    <p className="study-mode__section-desc">
                        Choose which unit to generate {modeLabel.toLowerCase()} questions for
                    </p>

                    <div className="study-mode__unit-grid">
                        {[1, 2, 3, 4, 5].map((num, i) => (
                            <button
                                key={num}
                                className="study-mode__unit-card card card-interactive"
                                onClick={() => handleSelectUnit(num)}
                                style={{
                                    '--subject-color': subject?.color || '#6366f1',
                                    animationDelay: `${i * 80}ms`,
                                }}
                            >
                                <span className="study-mode__unit-number">
                                    {String(num).padStart(2, '0')}
                                </span>
                                <span className="study-mode__unit-label">Unit {num}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 3: Questions + Answers View
    // ═══════════════════════════════════════════════════════════
    return (
        <div className="study-mode study-mode--active animate-fade-in">
            {/* ── Header ── */}
            <header className="study-mode__panel-header">
                <div className="study-mode__panel-header-left">
                    <button className="btn btn-ghost" onClick={handleReset}>
                        ← Back
                    </button>
                    <div className="study-mode__panel-info">
                        <span className="study-mode__panel-icon">{subject?.icon}</span>
                        <div>
                            <span className="study-mode__panel-subject">{subject?.shortName}</span>
                            <div className="study-mode__panel-badges">
                                <span className="badge badge-accent">Unit {selectedUnit}</span>
                                <span className={`badge ${selectedMode === '2_mark' ? 'badge-2mark' : 'badge-10mark'}`}>
                                    {modeIcon} {modeLabel}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {studentInfo && (
                    <span className="study-mode__panel-student">
                        👤 {studentInfo.name}
                    </span>
                )}
            </header>

            {/* ── Content Area ── */}
            <div className="study-mode__content">
                {/* ── Questions Panel ── */}
                <div className="study-mode__questions-panel">
                    <div className="study-mode__questions-header">
                        <h2>
                            {modeIcon} {modeLabel} Questions — {unitTitle || `Unit ${selectedUnit}`}
                        </h2>
                        <span className="study-mode__question-count badge badge-accent">
                            {questions.length} questions
                        </span>
                    </div>

                    {/* Loading state */}
                    {loadingQuestions && (
                        <div className="study-mode__loading">
                            <div className="study-mode__loading-spinner" />
                            <h3>Generating {modeLabel} Questions...</h3>
                            <p>Analyzing syllabus content for Unit {selectedUnit}</p>
                        </div>
                    )}

                    {/* Error state */}
                    {error && !loadingQuestions && (
                        <div className="study-mode__error card">
                            <span>⚠️</span>
                            <p>{error}</p>
                            <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => fetchQuestions(selectedUnit, selectedMode)}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {/* Question list */}
                    {!loadingQuestions && questions.length > 0 && (
                        <div className="study-mode__question-list">
                            {questions.map((q, i) => (
                                <button
                                    key={q.id}
                                    className={`study-mode__question-item ${
                                        activeQuestion === q.question ? 'study-mode__question-item--active' : ''
                                    }`}
                                    onClick={() => fetchAnswer(q.question)}
                                    style={{ animationDelay: `${i * 50}ms` }}
                                >
                                    <span className="study-mode__q-number">{q.id}</span>
                                    <span className="study-mode__q-text">{q.question}</span>
                                    <span className="study-mode__q-arrow">→</span>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Empty state */}
                    {!loadingQuestions && !error && questions.length === 0 && (
                        <div className="study-mode__empty">
                            <span className="study-mode__empty-icon">📋</span>
                            <p>No questions generated yet. Try again or upload syllabus materials.</p>
                        </div>
                    )}
                </div>

                {/* ── Answer Panel ── */}
                <div className="study-mode__answer-panel" ref={answerRef}>
                    {!activeQuestion && !loadingAnswer && (
                        <div className="study-mode__answer-placeholder">
                            <div className="study-mode__answer-placeholder-icon">✦</div>
                            <h3>Click a question to see the answer</h3>
                            <p>
                                AI will generate an exam-ready {modeLabel.toLowerCase()} answer
                                grounded in your syllabus materials.
                            </p>
                        </div>
                    )}

                    {loadingAnswer && (
                        <div className="study-mode__answer-loading">
                            <div className="study-mode__loading-spinner" />
                            <h3>Generating Answer...</h3>
                            <p className="study-mode__answer-loading-q">
                                "{activeQuestion}"
                            </p>
                        </div>
                    )}

                    {answer && !loadingAnswer && (
                        <div className="study-mode__answer-content animate-fade-in">
                            <div className="study-mode__answer-question-bar">
                                <span className="study-mode__answer-q-label">Q.</span>
                                <span>{activeQuestion}</span>
                            </div>
                            <div className="study-mode__answer-body">
                                <ChatMessage
                                    message={{
                                        role: 'assistant',
                                        content: answer,
                                        timestamp: new Date().toISOString(),
                                    }}
                                    isLast={true}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default StudyMode;
