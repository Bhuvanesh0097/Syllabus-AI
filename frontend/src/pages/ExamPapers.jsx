/**
 * ExamPapers Page — Browse and download question papers.
 * Flow: Select Exam Type → Select Section → Download subject papers.
 * Internal 2 & Model show "Coming Soon".
 */

import { useState, useCallback } from 'react';
import { SUBJECTS } from '../utils/constants';
import './ExamPapers.css';

/* ── Static exam data config ── */
const SECTIONS = ['A', 'B', 'C'];
const SUBJECT_KEYS = Object.keys(SUBJECTS); // COA, APJ, DAA, DM, OB

const EXAM_TYPES = [
    {
        id: 'internal1',
        label: 'Internal 1',
        icon: '📝',
        description: 'First internal assessment question papers',
        available: true,
    },
    {
        id: 'internal2',
        label: 'Internal 2',
        icon: '📋',
        description: 'Second internal assessment question papers',
        available: false,
    },
    {
        id: 'model',
        label: 'Model Question Papers',
        icon: '📖',
        description: 'Model exam question papers for final preparation',
        available: false,
    },
];

/**
 * Build the file path for a given exam type, section, and subject.
 * Files live in public/exam-papers/<examType>/<section>/<SUBJECT>.pdf
 */
function getPaperPath(examType, section, subjectCode) {
    return `/exam-papers/${examType}/${section}/${subjectCode}.pdf`;
}

function ExamPapers() {
    const [selectedExam, setSelectedExam] = useState(null);
    const [selectedSection, setSelectedSection] = useState(null);

    /* ── Navigation helpers ── */
    const goBackToExams = useCallback(() => {
        setSelectedExam(null);
        setSelectedSection(null);
    }, []);

    const goBackToSections = useCallback(() => {
        setSelectedSection(null);
    }, []);

    /* ── Download handler ── */
    const handleDownload = useCallback((subjectCode) => {
        if (!selectedExam || !selectedSection) return;
        const path = getPaperPath(selectedExam, selectedSection, subjectCode);
        const link = document.createElement('a');
        link.href = path;
        link.download = `${selectedExam}_Section-${selectedSection}_${subjectCode}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [selectedExam, selectedSection]);

    /* ═══════════════════════════════════════════════════════
     *  STEP 3 — Subject papers list (download page)
     * ═══════════════════════════════════════════════════════ */
    if (selectedExam && selectedSection) {
        const examLabel = EXAM_TYPES.find(e => e.id === selectedExam)?.label || selectedExam;

        return (
            <div className="exam-papers animate-fade-in">
                <div className="exam-papers__header">
                    <button className="btn btn-ghost" onClick={goBackToSections}>
                        ← Back
                    </button>
                    <div className="exam-papers__title-group">
                        <span className="exam-papers__header-icon">📄</span>
                        <div>
                            <h1 className="exam-papers__title">{examLabel}</h1>
                            <p className="exam-papers__subtitle">Section {selectedSection}</p>
                        </div>
                    </div>
                </div>

                <div className="exam-papers__breadcrumb">
                    <span onClick={goBackToExams}>Exam Papers</span>
                    <span className="exam-papers__breadcrumb-sep">›</span>
                    <span onClick={goBackToSections}>{examLabel}</span>
                    <span className="exam-papers__breadcrumb-sep">›</span>
                    <span className="exam-papers__breadcrumb-active">Section {selectedSection}</span>
                </div>

                <div className="exam-papers__section-heading">
                    <h2 className="exam-papers__section-title">Download Question Papers</h2>
                    <p className="exam-papers__section-desc">
                        Click on a subject below to download the {examLabel} question paper for Section {selectedSection}
                    </p>
                </div>

                <div className="exam-papers__subjects-grid">
                    {SUBJECT_KEYS.map((code, i) => {
                        const subj = SUBJECTS[code];
                        return (
                            <div
                                key={code}
                                className="exam-papers__subject-card card"
                                style={{
                                    '--subject-color': subj.color,
                                    animationDelay: `${i * 80}ms`,
                                }}
                            >
                                <div className="exam-papers__subject-top">
                                    <span className="exam-papers__subject-icon">{subj.icon}</span>
                                    <div className="exam-papers__subject-info">
                                        <span className="exam-papers__subject-code">{subj.code}</span>
                                        <span className="exam-papers__subject-name">{subj.name}</span>
                                    </div>
                                </div>
                                <div className="exam-papers__subject-meta">
                                    <span className="badge badge-accent">{examLabel}</span>
                                    <span className="badge">Section {selectedSection}</span>
                                </div>
                                <button
                                    className="exam-papers__download-btn"
                                    onClick={() => handleDownload(code)}
                                >
                                    <span className="exam-papers__download-icon">⬇</span>
                                    Download PDF
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════════
     *  STEP 2 — Section selection
     * ═══════════════════════════════════════════════════════ */
    if (selectedExam) {
        const examLabel = EXAM_TYPES.find(e => e.id === selectedExam)?.label || selectedExam;

        return (
            <div className="exam-papers animate-fade-in">
                <div className="exam-papers__header">
                    <button className="btn btn-ghost" onClick={goBackToExams}>
                        ← Back
                    </button>
                    <div className="exam-papers__title-group">
                        <span className="exam-papers__header-icon">📝</span>
                        <div>
                            <h1 className="exam-papers__title">{examLabel}</h1>
                            <p className="exam-papers__subtitle">Question Papers</p>
                        </div>
                    </div>
                </div>

                <div className="exam-papers__breadcrumb">
                    <span onClick={goBackToExams}>Exam Papers</span>
                    <span className="exam-papers__breadcrumb-sep">›</span>
                    <span className="exam-papers__breadcrumb-active">{examLabel}</span>
                </div>

                <div className="exam-papers__section-heading">
                    <h2 className="exam-papers__section-title">Select Your Section</h2>
                    <p className="exam-papers__section-desc">
                        Choose your section to view and download question papers
                    </p>
                </div>

                <div className="exam-papers__section-grid">
                    {SECTIONS.map((sec, i) => (
                        <button
                            key={sec}
                            className="exam-papers__section-card card card-interactive"
                            onClick={() => setSelectedSection(sec)}
                            style={{ animationDelay: `${i * 100}ms` }}
                        >
                            <span className="exam-papers__section-letter">{sec}</span>
                            <span className="exam-papers__section-label">Section {sec}</span>
                            <span className="exam-papers__section-count">{SUBJECT_KEYS.length} subjects</span>
                            <span className="exam-papers__section-arrow">View Papers →</span>
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════════
     *  STEP 1 — Exam type selection
     * ═══════════════════════════════════════════════════════ */
    return (
        <div className="exam-papers animate-fade-in">
            <div className="exam-papers__header">
                <div className="exam-papers__title-group">
                    <span className="exam-papers__header-icon">📄</span>
                    <div>
                        <h1 className="exam-papers__title">Exam Papers</h1>
                        <p className="exam-papers__subtitle">Browse & download question papers</p>
                    </div>
                </div>
            </div>

            <div className="exam-papers__section-heading">
                <h2 className="exam-papers__section-title">Choose Exam Type</h2>
                <p className="exam-papers__section-desc">
                    Select the type of exam papers you want to access
                </p>
            </div>

            <div className="exam-papers__type-grid">
                {EXAM_TYPES.map((exam, i) => (
                    <button
                        key={exam.id}
                        className={`exam-papers__type-card card ${exam.available ? 'card-interactive' : 'exam-papers__type-card--locked'}`}
                        onClick={() => exam.available && setSelectedExam(exam.id)}
                        disabled={!exam.available}
                        style={{ animationDelay: `${i * 100}ms` }}
                    >
                        {!exam.available && (
                            <div className="exam-papers__coming-soon-overlay">
                                <span className="exam-papers__coming-soon-badge">🔒 Coming Soon</span>
                            </div>
                        )}
                        <span className="exam-papers__type-icon">{exam.icon}</span>
                        <h3 className="exam-papers__type-label">{exam.label}</h3>
                        <p className="exam-papers__type-desc">{exam.description}</p>
                        {exam.available && (
                            <span className="exam-papers__type-action">Browse Papers →</span>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default ExamPapers;
