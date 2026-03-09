/**
 * Application constants.
 */

export const SUBJECTS = {
    COA: {
        code: 'COA',
        name: 'Computer Organization and Architecture',
        shortName: 'COA',
        icon: '🖥️',
        color: '#6366f1',
    },
    APJ: {
        code: 'APJ',
        name: 'Advanced Programming in Java',
        shortName: 'Java',
        icon: '☕',
        color: '#f59e0b',
    },
    DAA: {
        code: 'DAA',
        name: 'Design and Analysis of Algorithms',
        shortName: 'Algorithms',
        icon: '⚡',
        color: '#10b981',
    },
    DM: {
        code: 'DM',
        name: 'Discrete Mathematics',
        shortName: 'Discrete Math',
        icon: '🔢',
        color: '#8b5cf6',
    },
    OB: {
        code: 'OB',
        name: 'Organizational Behaviour',
        shortName: 'OB',
        icon: '👥',
        color: '#ec4899',
    },
};

export const ANSWER_STYLES = [
    { value: '2_mark', label: '2 Mark', description: 'Short, exam-ready answers' },
    { value: '10_mark', label: '10 Mark', description: 'Detailed, structured answers' },
    { value: 'explanation', label: 'Explain', description: 'Clear explanations with examples' },
    { value: 'summary', label: 'Summary', description: 'Bullet-point overview' },
    { value: 'quick_revision', label: 'Quick Revise', description: 'Key points only' },
];

export const APP_INFO = {
    name: 'Syllabus AI',
    version: '1.0.0',
    tagline: 'Your Intelligent Study Companion',
    department: 'Computer Science Engineering',
    year: '2nd Year',
    semester: '4th Semester',
};
