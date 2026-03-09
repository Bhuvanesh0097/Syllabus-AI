/**
 * UnitSelector Component — lets users pick a unit within a subject.
 */

import { SUBJECTS } from '../utils/constants';
import './UnitSelector.css';

function UnitSelector({ subjectCode, units, selectedUnit, onSelect, onBack }) {
    const subject = SUBJECTS[subjectCode];

    return (
        <div className="unit-selector animate-fade-in">
            <div className="unit-selector__header">
                <button className="btn btn-ghost" onClick={onBack}>
                    ← Back
                </button>
                <div className="unit-selector__title">
                    <span className="unit-selector__icon">{subject?.icon}</span>
                    <h2>{subject?.name || subjectCode}</h2>
                </div>
                <p className="unit-selector__subtitle">Select a unit to begin studying</p>
            </div>

            <div className="unit-selector__grid">
                {(units || [1, 2, 3, 4, 5].map(n => ({ number: n, title: `Unit ${n}` }))).map((unit, i) => (
                    <button
                        key={unit.number}
                        className={`unit-selector__item card card-interactive ${selectedUnit === unit.number ? 'unit-selector__item--active' : ''
                            }`}
                        onClick={() => onSelect(unit.number)}
                        style={{
                            '--subject-color': subject?.color || '#6366f1',
                            animationDelay: `${i * 80}ms`,
                        }}
                    >
                        <span className="unit-selector__number">
                            {String(unit.number).padStart(2, '0')}
                        </span>
                        <span className="unit-selector__unit-title">
                            {unit.title || `Unit ${unit.number}`}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
}

export default UnitSelector;
