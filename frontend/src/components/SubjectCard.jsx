/**
 * SubjectCard Component — displays a subject with visual indicators.
 */

import { SUBJECTS } from '../utils/constants';
import './SubjectCard.css';

function SubjectCard({ subject, onClick, delay = 0 }) {
    const subjectInfo = SUBJECTS[subject.code] || subject;

    return (
        <div
            className="subject-card card card-interactive card-glow"
            onClick={() => onClick(subject.code)}
            style={{
                '--subject-color': subjectInfo.color,
                animationDelay: `${delay}ms`,
            }}
        >
            <div className="subject-card__glow" />

            <div className="subject-card__header">
                <span className="subject-card__icon">{subjectInfo.icon}</span>
                <span className="subject-card__code badge">{subject.code}</span>
            </div>

            <h3 className="subject-card__name">{subject.name}</h3>
            <p className="subject-card__desc">{subject.description}</p>

            <div className="subject-card__units">
                {(subject.units || []).slice(0, 5).map((unit, i) => (
                    <div
                        key={i}
                        className="subject-card__unit-dot"
                        title={unit.title || `Unit ${unit.number}`}
                    />
                ))}
                <span className="subject-card__unit-label">5 Units</span>
            </div>

            <div className="subject-card__action">
                <span>Start Preparing</span>
                <span className="subject-card__arrow">→</span>
            </div>
        </div>
    );
}

export default SubjectCard;
