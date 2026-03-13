import { useState, useEffect, useCallback, useRef } from 'react';
import { APP_INFO, SUBJECTS } from '../utils/constants';
import api from '../api/client';
import './Landing.css';

const DEPARTMENTS = ['CSE'];
const YEARS = ['2nd Year'];
const SEMESTERS = ['4th Semester'];
const SECTIONS = ['A', 'B', 'C'];
const UNITS = [
    { value: 1, label: 'Unit 1' },
    { value: 2, label: 'Unit 2' },
    { value: 3, label: 'Unit 3' },
    { value: 4, label: 'Unit 4' },
    { value: 5, label: 'Unit 5' },
];

function Landing({ onStartPreparation }) {
    const [formData, setFormData] = useState({
        name: '',
        department: 'CSE',
        year: '2nd Year',
        semester: '4th Semester',
        section: '',
        subject: '',
        unit: '',
    });

    const [focusedField, setFocusedField] = useState(null);
    const [errors, setErrors] = useState({});
    const [welcomeBack, setWelcomeBack] = useState(null);
    const nameDebounceRef = useRef(null);

    const subjectList = Object.values(SUBJECTS);

    // Check for returning student on mount
    useEffect(() => {
        const checkReturning = async () => {
            try {
                const res = await api.getProfile();
                if (res.exists && res.profile?.name) {
                    const profile = res.profile;
                    setFormData(prev => ({
                        ...prev,
                        name: profile.name,
                        section: profile.section || prev.section,
                    }));
                    // Fetch welcome-back data
                    const wb = await api.getWelcomeBack();
                    if (wb.returning && wb.data) {
                        setWelcomeBack(wb.data);
                        // Pre-fill last session subject/unit
                        const lastSession = wb.data.last_session;
                        if (lastSession) {
                            setFormData(prev => ({
                                ...prev,
                                subject: lastSession.subject_code || prev.subject,
                                unit: wb.data.suggested_unit || '',
                            }));
                        }
                    }
                }
            } catch (err) {
                // No saved profile — first-time student
            }
        };
        checkReturning();
    }, []);

    // Debounced name lookup for returning students
    const handleNameChange = useCallback((value) => {
        setFormData(prev => ({ ...prev, name: value }));
        if (errors.name) setErrors(prev => ({ ...prev, name: '' }));

        if (nameDebounceRef.current) clearTimeout(nameDebounceRef.current);
        if (value.trim().length >= 2) {
            nameDebounceRef.current = setTimeout(async () => {
                try {
                    const wb = await api.getWelcomeBackByName(value.trim());
                    if (wb.returning && wb.data) {
                        setWelcomeBack(wb.data);
                        const lastSession = wb.data.last_session;
                        if (lastSession) {
                            setFormData(prev => ({
                                ...prev,
                                subject: prev.subject || lastSession.subject_code,
                                unit: prev.unit || wb.data.suggested_unit || '',
                            }));
                        }
                    } else {
                        setWelcomeBack(null);
                    }
                } catch {
                    setWelcomeBack(null);
                }
            }, 600);
        } else {
            setWelcomeBack(null);
        }
    }, [errors]);

    const updateField = (field, value) => {
        if (field === 'name') {
            handleNameChange(value);
            return;
        }
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const validate = () => {
        const newErrors = {};
        if (!formData.name.trim()) newErrors.name = 'Please enter your name';
        if (!formData.section) newErrors.section = 'Please select your section';
        if (!formData.subject) newErrors.subject = 'Please select a subject';
        if (!formData.unit) newErrors.unit = 'Please select a unit';
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (validate()) {
            onStartPreparation({
                ...formData,
                unit: parseInt(formData.unit),
            });
        }
    };

    const selectedSubject = subjectList.find(s => s.code === formData.subject);
    const isFormValid = formData.name.trim() && formData.section && formData.subject && formData.unit;

    return (
        <div className="landing">
            {/* ── Background Effects ── */}
            <div className="landing__orb landing__orb--1" />
            <div className="landing__orb landing__orb--2" />
            <div className="landing__orb landing__orb--3" />

            <div className="landing__container">
                {/* ── Left Panel: Branding ── */}
                <div className="landing__brand animate-fade-in-up">
                    <div className="landing__badge badge badge-accent">
                        ✦ AI-Powered Study Assistant
                    </div>

                    <h1 className="landing__title">
                        <span className="gradient-text-vivid">Nexora</span>
                    </h1>

                    <p className="landing__subtitle">
                        Your intelligent exam preparation companion.
                        <br />
                        Grounded strictly in your syllabus materials.
                    </p>

                    <div className="landing__features-list">
                        {[
                            { icon: '📝', text: '2-Mark & 10-Mark Exam Prep' },
                            { icon: '🧠', text: 'Remembers Your Progress' },
                            { icon: '📅', text: 'Smart Study Planner' },
                            { icon: '📚', text: '100% Syllabus Grounded' },
                            { icon: '💬', text: 'ChatGPT-Style Tutoring' },
                        ].map((feature, i) => (
                            <div
                                key={feature.text}
                                className="landing__feature-item"
                                style={{ animationDelay: `${300 + i * 100}ms` }}
                            >
                                <span className="landing__feature-icon">{feature.icon}</span>
                                <span className="landing__feature-text">{feature.text}</span>
                            </div>
                        ))}
                    </div>

                    <div className="landing__dept-info">
                        <span>{APP_INFO.department}</span>
                        <span className="landing__dept-divider">·</span>
                        <span>{APP_INFO.year}</span>
                        <span className="landing__dept-divider">·</span>
                        <span>{APP_INFO.semester}</span>
                    </div>
                </div>

                {/* ── Right Panel: Setup Form ── */}
                <form className="landing__form glass-strong animate-fade-in-up" onSubmit={handleSubmit} style={{ animationDelay: '150ms' }}>
                    <div className="landing__form-header">
                        <h2 className="landing__form-title">
                            {welcomeBack ? `Welcome Back! 👋` : 'Start Your Study Session'}
                        </h2>
                        <p className="landing__form-desc">
                            {welcomeBack
                                ? 'Great to see you again. Pick up where you left off!'
                                : 'Fill in your details to begin exam preparation'
                            }
                        </p>
                    </div>

                    {/* ── Welcome Back Banner ── */}
                    {welcomeBack && (
                        <div className="landing__welcome-back animate-fade-in">
                            <div className="landing__wb-greeting">
                                Welcome back, <strong>{welcomeBack.name}</strong>! 🎉
                            </div>
                            <div className="landing__wb-details">
                                {welcomeBack.last_session && (
                                    <div className="landing__wb-item">
                                        <span className="landing__wb-icon">📖</span>
                                        <span>
                                            Last studied: <strong>
                                                {welcomeBack.last_session.subject_code} — Unit {welcomeBack.last_session.unit_number}
                                            </strong>
                                        </span>
                                    </div>
                                )}
                                {welcomeBack.total_topics > 0 && (
                                    <div className="landing__wb-item">
                                        <span className="landing__wb-icon">🧠</span>
                                        <span>{welcomeBack.total_topics} topics covered across {welcomeBack.subjects_studied?.length || 0} subject(s)</span>
                                    </div>
                                )}
                                {welcomeBack.suggested_unit && welcomeBack.last_session && (
                                    <div className="landing__wb-item landing__wb-suggestion">
                                        <span className="landing__wb-icon">💡</span>
                                        <span>
                                            Would you like to continue with <strong>Unit {welcomeBack.suggested_unit}</strong>?
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── Name ── */}
                    <div className={`landing__field ${focusedField === 'name' ? 'landing__field--focused' : ''} ${errors.name ? 'landing__field--error' : ''}`}>
                        <label className="landing__label" htmlFor="student-name">
                            <span className="landing__label-icon">👤</span>
                            Your Name
                        </label>
                        <input
                            id="student-name"
                            type="text"
                            className="landing__input"
                            placeholder="Enter your name"
                            value={formData.name}
                            onChange={(e) => updateField('name', e.target.value)}
                            onFocus={() => setFocusedField('name')}
                            onBlur={() => setFocusedField(null)}
                            autoComplete="off"
                        />
                        {errors.name && <span className="landing__error">{errors.name}</span>}
                    </div>

                    {/* ── Department & Year (side by side) ── */}
                    <div className="landing__field-row">
                        <div className="landing__field landing__field--readonly">
                            <label className="landing__label">
                                <span className="landing__label-icon">🏛️</span>
                                Department
                            </label>
                            <div className="landing__static-value">{formData.department}</div>
                        </div>

                        <div className="landing__field landing__field--readonly">
                            <label className="landing__label">
                                <span className="landing__label-icon">📅</span>
                                Year
                            </label>
                            <div className="landing__static-value">{formData.year}</div>
                        </div>
                    </div>

                    {/* ── Semester & Section (side by side) ── */}
                    <div className="landing__field-row">
                        <div className="landing__field landing__field--readonly">
                            <label className="landing__label">
                                <span className="landing__label-icon">📖</span>
                                Semester
                            </label>
                            <div className="landing__static-value">{formData.semester}</div>
                        </div>

                        <div className={`landing__field ${errors.section ? 'landing__field--error' : ''}`}>
                            <label className="landing__label" htmlFor="student-section">
                                <span className="landing__label-icon">🔤</span>
                                Section
                            </label>
                            <div className="landing__section-options">
                                {SECTIONS.map((sec) => (
                                    <button
                                        key={sec}
                                        type="button"
                                        className={`landing__section-btn ${formData.section === sec ? 'landing__section-btn--active' : ''}`}
                                        onClick={() => updateField('section', sec)}
                                    >
                                        {sec}
                                    </button>
                                ))}
                            </div>
                            {errors.section && <span className="landing__error">{errors.section}</span>}
                        </div>
                    </div>

                    {/* ── Subject Selection ── */}
                    <div className={`landing__field ${errors.subject ? 'landing__field--error' : ''}`}>
                        <label className="landing__label">
                            <span className="landing__label-icon">📚</span>
                            Select Subject
                        </label>
                        <div className="landing__subject-grid">
                            {subjectList.map((subject) => (
                                <button
                                    key={subject.code}
                                    type="button"
                                    className={`landing__subject-chip ${formData.subject === subject.code ? 'landing__subject-chip--active' : ''}`}
                                    style={{ '--chip-color': subject.color }}
                                    onClick={() => updateField('subject', subject.code)}
                                >
                                    <span className="landing__subject-chip-icon">{subject.icon}</span>
                                    <span className="landing__subject-chip-label">{subject.code}</span>
                                </button>
                            ))}
                        </div>
                        {selectedSubject && (
                            <p className="landing__subject-full-name">{selectedSubject.name}</p>
                        )}
                        {errors.subject && <span className="landing__error">{errors.subject}</span>}
                    </div>

                    {/* ── Unit Selection ── */}
                    <div className={`landing__field ${errors.unit ? 'landing__field--error' : ''}`}>
                        <label className="landing__label">
                            <span className="landing__label-icon">📋</span>
                            Select Unit
                        </label>
                        <div className="landing__unit-grid">
                            {UNITS.map((unit) => (
                                <button
                                    key={unit.value}
                                    type="button"
                                    className={`landing__unit-btn ${formData.unit == unit.value ? 'landing__unit-btn--active' : ''}`}
                                    style={{ '--chip-color': selectedSubject?.color || 'var(--accent-primary)' }}
                                    onClick={() => updateField('unit', unit.value)}
                                >
                                    <span className="landing__unit-num">{String(unit.value).padStart(2, '0')}</span>
                                    <span className="landing__unit-label">{unit.label}</span>
                                </button>
                            ))}
                        </div>
                        {errors.unit && <span className="landing__error">{errors.unit}</span>}
                    </div>

                    {/* ── Submit Button ── */}
                    <button
                        type="submit"
                        className={`landing__submit-btn ${isFormValid ? 'landing__submit-btn--ready' : ''}`}
                        disabled={!isFormValid}
                    >
                        <span className="landing__submit-text">START PREPARATION</span>
                        <span className="landing__submit-arrow">→</span>
                    </button>

                    {isFormValid && (
                        <p className="landing__ready-msg animate-fade-in">
                            ✦ Ready to study <strong>{selectedSubject?.shortName}</strong> — Unit {formData.unit}
                        </p>
                    )}
                </form>
            </div>
        </div>
    );
}

export default Landing;
