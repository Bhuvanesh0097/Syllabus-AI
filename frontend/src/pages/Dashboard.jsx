/**
 * Dashboard Page — subject selection grid.
 */

import { useState, useEffect } from 'react';
import SubjectCard from '../components/SubjectCard';
import api from '../api/client';
import { APP_INFO } from '../utils/constants';
import './Dashboard.css';

function Dashboard({ onSelectSubject }) {
    const [subjects, setSubjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadSubjects();
    }, []);

    const loadSubjects = async () => {
        try {
            setLoading(true);
            const data = await api.getSubjects();
            setSubjects(data.subjects || []);
        } catch (err) {
            setError(err.message);
            // Fallback to local constants
            const { SUBJECTS } = await import('../utils/constants');
            setSubjects(Object.values(SUBJECTS).map(s => ({
                ...s,
                name: s.name,
                description: '',
                units: [1, 2, 3, 4, 5].map(n => ({ number: n, title: `Unit ${n}` })),
            })));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="dashboard">
            <div className="dashboard__header animate-fade-in">
                <div className="dashboard__greeting">
                    <h1>
                        Welcome to <span className="gradient-text-vivid">{APP_INFO.name}</span>
                    </h1>
                    <p className="dashboard__tagline">
                        Choose a subject to start your exam preparation journey
                    </p>
                </div>

                <div className="dashboard__meta">
                    <span className="badge badge-accent">
                        {APP_INFO.semester}
                    </span>
                </div>
            </div>

            {error && (
                <div className="dashboard__notice">
                    <span>⚠️ Running in offline mode — backend not connected</span>
                </div>
            )}

            {loading ? (
                <div className="dashboard__loading">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="dashboard__skeleton card" />
                    ))}
                </div>
            ) : (
                <div className="dashboard__grid">
                    {subjects.map((subject, i) => (
                        <SubjectCard
                            key={subject.code}
                            subject={subject}
                            onClick={onSelectSubject}
                            delay={i * 100}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default Dashboard;
