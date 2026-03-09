/**
 * Documents Page — Upload syllabus documents and view RAG knowledge base status.
 * Full pipeline: Upload → Extract → Chunk → Embed → Store in ChromaDB
 * Supports per-section (A, B, C) document management.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SUBJECTS } from '../utils/constants';
import api from '../api/client';
import './Documents.css';

const SECTIONS = ['A', 'B', 'C'];

function Documents({ onBack }) {
    const [selectedSubject, setSelectedSubject] = useState(null);
    const [selectedSection, setSelectedSection] = useState('A');
    const [selectedUnit, setSelectedUnit] = useState(1);
    const [documents, setDocuments] = useState([]);
    const [stats, setStats] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    // Load documents + stats when subject or section changes
    const loadData = useCallback(async (subjectCode, section) => {
        if (!subjectCode) return;
        setLoading(true);
        setError(null);
        try {
            const [docsRes, statsRes] = await Promise.all([
                api.getDocuments(subjectCode, section),
                api.getDocumentStats(subjectCode, section),
            ]);
            setDocuments(docsRes.documents || []);
            setStats(statsRes);
        } catch (err) {
            console.error('Failed to load documents:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (selectedSubject) loadData(selectedSubject, selectedSection);
    }, [selectedSubject, selectedSection, loadData]);

    // Handle file upload
    const handleUpload = useCallback(async (e) => {
        const files = e.target.files;
        if (!files?.length || !selectedSubject) return;

        setUploading(true);
        setUploadProgress({ current: 0, total: files.length, results: [] });

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            setUploadProgress(prev => ({
                ...prev,
                current: i + 1,
                currentFile: file.name,
            }));

            try {
                const result = await api.uploadDocument(file, selectedSubject, selectedUnit, selectedSection);
                setUploadProgress(prev => ({
                    ...prev,
                    results: [...prev.results, {
                        filename: file.name,
                        success: true,
                        chunks: result.chunks_created,
                        message: result.message,
                    }],
                }));
            } catch (err) {
                setUploadProgress(prev => ({
                    ...prev,
                    results: [...prev.results, {
                        filename: file.name,
                        success: false,
                        message: err.message,
                    }],
                }));
            }
        }

        setUploading(false);
        // Refresh data
        await loadData(selectedSubject, selectedSection);
        // Reset input
        if (fileInputRef.current) fileInputRef.current.value = '';
    }, [selectedSubject, selectedUnit, selectedSection, loadData]);

    // Handle file delete
    const handleDelete = useCallback(async (filename) => {
        if (!window.confirm(`Delete "${filename}" and remove all its chunks from the knowledge base (Section ${selectedSection})?`)) {
            return;
        }
        try {
            await api.deleteDocument(selectedSubject, filename, selectedSection);
            await loadData(selectedSubject, selectedSection);
        } catch (err) {
            setError(err.message);
        }
    }, [selectedSubject, selectedSection, loadData]);

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    // ═════════════════════════════════════════════════════════
    // Step 1: Subject Selection
    // ═════════════════════════════════════════════════════════
    if (!selectedSubject) {
        return (
            <div className="documents animate-fade-in">
                <div className="documents__header">
                    <button className="btn btn-ghost" onClick={onBack}>← Back</button>
                    <div className="documents__title-group">
                        <span className="documents__icon">📚</span>
                        <div>
                            <h1 className="documents__title">Knowledge Base</h1>
                            <p className="documents__subtitle">
                                Upload syllabus materials to power the RAG system
                            </p>
                        </div>
                    </div>
                </div>

                <div className="documents__subject-select">
                    <h2 className="documents__section-title">Select a Subject</h2>
                    <p className="documents__section-desc">
                        Choose which subject to manage documents for.
                        Each subject has sections A, B, C for different classes.
                    </p>

                    <div className="documents__subject-grid">
                        {Object.values(SUBJECTS).map((subject, i) => (
                            <button
                                key={subject.code}
                                className="documents__subject-card card card-interactive"
                                onClick={() => setSelectedSubject(subject.code)}
                                style={{
                                    '--subject-color': subject.color,
                                    animationDelay: `${i * 80}ms`,
                                }}
                            >
                                <span className="documents__subject-emoji">{subject.icon}</span>
                                <h3>{subject.shortName}</h3>
                                <p>{subject.name}</p>
                                <div className="documents__subject-sections">
                                    {SECTIONS.map((s) => (
                                        <span key={s} className="documents__section-badge">Sec {s}</span>
                                    ))}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Pipeline Visualization */}
                <div className="documents__pipeline">
                    <h3 className="documents__pipeline-title">RAG Pipeline</h3>
                    <div className="documents__pipeline-steps">
                        {[
                            { icon: '📄', label: 'Upload', desc: 'PDF, PPTX, DOCX' },
                            { icon: '📝', label: 'Extract', desc: 'Text extraction' },
                            { icon: '✂️', label: 'Chunk', desc: '500w / 100w overlap' },
                            { icon: '🧬', label: 'Embed', desc: 'Vector embeddings' },
                            { icon: '🗄️', label: 'Store', desc: 'ChromaDB' },
                        ].map((step, i) => (
                            <div key={step.label} className="documents__pipeline-step" style={{ animationDelay: `${i * 100}ms` }}>
                                <span className="documents__pipeline-icon">{step.icon}</span>
                                <span className="documents__pipeline-label">{step.label}</span>
                                <span className="documents__pipeline-desc">{step.desc}</span>
                                {i < 4 && <span className="documents__pipeline-arrow">→</span>}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    const subject = SUBJECTS[selectedSubject];

    // ═════════════════════════════════════════════════════════
    // Step 2: Document Management Dashboard
    // ═════════════════════════════════════════════════════════
    return (
        <div className="documents documents--active animate-fade-in">
            {/* Header */}
            <div className="documents__header">
                <button className="btn btn-ghost" onClick={() => setSelectedSubject(null)}>
                    ← Subjects
                </button>
                <div className="documents__title-group">
                    <span className="documents__icon">{subject?.icon}</span>
                    <div>
                        <h1 className="documents__title">
                            {subject?.shortName} Knowledge Base
                        </h1>
                        <p className="documents__subtitle">{subject?.name}</p>
                    </div>
                </div>
            </div>

            {/* Section Selector */}
            <div className="documents__section-selector">
                <label className="documents__section-selector-label">📋 Section:</label>
                <div className="documents__section-buttons">
                    {SECTIONS.map((sec) => (
                        <button
                            key={sec}
                            className={`documents__section-btn ${selectedSection === sec ? 'documents__section-btn--active' : ''}`}
                            onClick={() => setSelectedSection(sec)}
                        >
                            Section {sec}
                        </button>
                    ))}
                </div>
                <span className="documents__section-hint">
                    Each section has its own notes and PDFs
                </span>
            </div>

            {/* Stats Bar */}
            {stats && (
                <div className="documents__stats-bar">
                    <div className="documents__stat">
                        <span className="documents__stat-value">{stats.total_documents}</span>
                        <span className="documents__stat-label">Documents</span>
                    </div>
                    <div className="documents__stat">
                        <span className="documents__stat-value">{stats.total_chunks}</span>
                        <span className="documents__stat-label">Chunks</span>
                    </div>
                    <div className="documents__stat">
                        <span className="documents__stat-value">{stats.units_ready}/5</span>
                        <span className="documents__stat-label">Units Ready</span>
                    </div>
                    <div className="documents__stat">
                        <span className={`documents__stat-badge ${stats.rag_status === 'ready' ? 'documents__stat-badge--ready' : ''}`}>
                            {stats.rag_status === 'ready' ? '● Active' : '○ Empty'}
                        </span>
                        <span className="documents__stat-label">RAG Status</span>
                    </div>
                    <div className="documents__stat">
                        <span className="documents__stat-badge documents__stat-badge--section">
                            Sec {selectedSection}
                        </span>
                        <span className="documents__stat-label">Section</span>
                    </div>
                </div>
            )}

            {/* Unit Stats Grid */}
            {stats?.units && (
                <div className="documents__unit-stats">
                    {[1, 2, 3, 4, 5].map((num) => {
                        const unitKey = `unit_${num}`;
                        const unitStat = stats.units[unitKey] || {};
                        const isReady = unitStat.status === 'ready';
                        return (
                            <div
                                key={num}
                                className={`documents__unit-stat-card ${isReady ? 'documents__unit-stat-card--ready' : ''}`}
                            >
                                <span className="documents__unit-stat-num">U{num}</span>
                                <span className="documents__unit-stat-chunks">
                                    {unitStat.chunks || 0} chunks
                                </span>
                                <span className={`documents__unit-status ${isReady ? 'documents__unit-status--ready' : ''}`}>
                                    {isReady ? '✓' : '—'}
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Upload Section */}
            <div className="documents__upload-section">
                <div className="documents__upload-controls">
                    <div className="documents__unit-picker">
                        <label>Upload to Unit:</label>
                        <div className="documents__unit-buttons">
                            {[1, 2, 3, 4, 5].map((num) => (
                                <button
                                    key={num}
                                    className={`documents__unit-btn ${selectedUnit === num ? 'documents__unit-btn--active' : ''}`}
                                    onClick={() => setSelectedUnit(num)}
                                >
                                    {num}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="documents__upload-area">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf,.pptx,.ppt,.docx,.doc,.txt"
                            multiple
                            onChange={handleUpload}
                            className="documents__file-input"
                            id="file-upload"
                            disabled={uploading}
                        />
                        <label
                            htmlFor="file-upload"
                            className={`documents__upload-label ${uploading ? 'documents__upload-label--disabled' : ''}`}
                        >
                            <span className="documents__upload-icon">📎</span>
                            <span className="documents__upload-text">
                                {uploading
                                    ? `Processing ${uploadProgress?.currentFile}...`
                                    : `Upload to ${subject?.shortName} Section ${selectedSection} — Unit ${selectedUnit}`
                                }
                            </span>
                            <span className="documents__upload-hint">
                                Files are processed through the RAG pipeline automatically
                            </span>
                        </label>
                    </div>
                </div>

                {/* Upload Progress */}
                {uploadProgress?.results?.length > 0 && (
                    <div className="documents__upload-results">
                        {uploadProgress.results.map((r, i) => (
                            <div
                                key={i}
                                className={`documents__upload-result ${r.success ? 'documents__upload-result--success' : 'documents__upload-result--error'}`}
                            >
                                <span>{r.success ? '✓' : '✗'}</span>
                                <span className="documents__upload-result-name">{r.filename}</span>
                                <span className="documents__upload-result-msg">
                                    {r.success ? `${r.chunks} chunks indexed` : r.message}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="documents__error">
                    <span>⚠️</span> {error}
                </div>
            )}

            {/* Document List */}
            <div className="documents__list-section">
                <h3 className="documents__list-title">
                    Section {selectedSection} — Uploaded Documents ({documents.length})
                </h3>

                {loading && (
                    <div className="documents__loading">
                        <div className="study-mode__loading-spinner" />
                        <p>Loading documents...</p>
                    </div>
                )}

                {!loading && documents.length === 0 && (
                    <div className="documents__empty">
                        <span className="documents__empty-icon">📋</span>
                        <h4>No documents in Section {selectedSection}</h4>
                        <p>
                            Upload syllabus PDFs, presentations, or notes for Section {selectedSection} to power the AI
                            with your actual course materials for this class.
                        </p>
                    </div>
                )}

                {!loading && documents.length > 0 && (
                    <div className="documents__list">
                        {documents.map((doc, i) => (
                            <div key={doc.filename} className="documents__doc-item" style={{ animationDelay: `${i * 40}ms` }}>
                                <span className="documents__doc-icon">
                                    {doc.filename.endsWith('.pdf') ? '📕' :
                                     doc.filename.endsWith('.pptx') || doc.filename.endsWith('.ppt') ? '📊' :
                                     doc.filename.endsWith('.docx') || doc.filename.endsWith('.doc') ? '📘' : '📄'}
                                </span>
                                <div className="documents__doc-info">
                                    <span className="documents__doc-name">{doc.filename}</span>
                                    <span className="documents__doc-meta">
                                        {formatSize(doc.size_bytes)} • Section {selectedSection}
                                    </span>
                                </div>
                                <button
                                    className="documents__doc-delete"
                                    onClick={() => handleDelete(doc.filename)}
                                    title="Delete document"
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default Documents;
