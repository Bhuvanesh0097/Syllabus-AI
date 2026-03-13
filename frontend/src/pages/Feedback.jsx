/**
 * Feedback Page — Star rating + comment form with WhatsApp automation.
 * Sends feedback to the backend AND opens WhatsApp with a pre-filled message.
 */

import { useState, useCallback } from 'react';
import api from '../api/client';
import './Feedback.css';

const STAR_LABELS = ['Terrible', 'Poor', 'Average', 'Good', 'Excellent'];
const WHATSAPP_PHONE = '918825921420';

function Feedback({ studentInfo }) {
    const [rating, setRating] = useState(0);
    const [hoverRating, setHoverRating] = useState(0);
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const activeRating = hoverRating || rating;

    const handleSubmit = useCallback(async () => {
        if (rating === 0) {
            setError('Please select a star rating');
            return;
        }

        setSubmitting(true);
        setError('');

        try {
            const result = await api.submitFeedback(
                rating,
                comment,
                studentInfo?.name || '',
                studentInfo?.section || ''
            );

            if (result.success) {
                setSubmitted(true);

                // Open WhatsApp with pre-filled feedback message
                if (result.whatsapp_link) {
                    window.open(result.whatsapp_link, '_blank');
                }
            }
        } catch (err) {
            console.error('Feedback submission failed:', err);
            // Even if backend fails, still open WhatsApp with a client-generated link
            const fallbackLink = _buildWhatsAppLink(rating, comment, studentInfo?.name);
            window.open(fallbackLink, '_blank');
            setSubmitted(true);
        } finally {
            setSubmitting(false);
        }
    }, [rating, comment, studentInfo]);

    const handleReset = useCallback(() => {
        setRating(0);
        setHoverRating(0);
        setComment('');
        setSubmitted(false);
        setError('');
    }, []);

    // ── Success State ──
    if (submitted) {
        return (
            <div className="feedback">
                <div className="feedback__success animate-fade-in">
                    <div className="feedback__success-icon">🎉</div>
                    <h2 className="feedback__success-title">Thank You!</h2>
                    <p className="feedback__success-text">
                        Your feedback has been recorded. A WhatsApp message has been
                        prepared — just hit <strong>Send</strong> in WhatsApp to deliver it!
                    </p>
                    <div className="feedback__success-stars">
                        {'⭐'.repeat(rating)}
                    </div>
                    {comment && (
                        <p className="feedback__success-comment">"{comment}"</p>
                    )}
                    <div className="feedback__success-actions">
                        <button className="feedback__btn feedback__btn--secondary" onClick={handleReset}>
                            Submit Another
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ── Feedback Form ──
    return (
        <div className="feedback">
            <div className="feedback__header">
                <h1 className="feedback__title">💬 Feedback</h1>
                <p className="feedback__subtitle">
                    Help us improve Nexora — your rating goes directly to our WhatsApp!
                </p>
            </div>

            <div className="feedback__card glass-strong">
                {/* WhatsApp Badge */}
                <div className="feedback__whatsapp-badge">
                    <svg className="feedback__whatsapp-icon" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                    </svg>
                    <span>Feedback sent via WhatsApp</span>
                </div>

                {/* Star Rating */}
                <div className="feedback__rating-section">
                    <h3 className="feedback__section-label">How would you rate your experience?</h3>

                    <div className="feedback__stars">
                        {[1, 2, 3, 4, 5].map((star) => (
                            <button
                                key={star}
                                className={`feedback__star ${star <= activeRating ? 'feedback__star--active' : ''} ${star <= rating ? 'feedback__star--selected' : ''}`}
                                onClick={() => { setRating(star); setError(''); }}
                                onMouseEnter={() => setHoverRating(star)}
                                onMouseLeave={() => setHoverRating(0)}
                                aria-label={`${star} star`}
                            >
                                <svg viewBox="0 0 24 24" width="40" height="40">
                                    <path
                                        d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                                        fill={star <= activeRating ? 'currentColor' : 'none'}
                                        stroke="currentColor"
                                        strokeWidth="1.5"
                                        strokeLinejoin="round"
                                    />
                                </svg>
                            </button>
                        ))}
                    </div>

                    {activeRating > 0 && (
                        <span className="feedback__rating-label animate-fade-in">
                            {STAR_LABELS[activeRating - 1]}
                        </span>
                    )}
                </div>

                {/* Comment */}
                <div className="feedback__comment-section">
                    <h3 className="feedback__section-label">Any additional thoughts? (optional)</h3>
                    <textarea
                        className="feedback__textarea"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Tell us what you liked or what we can improve..."
                        rows={4}
                        maxLength={1000}
                    />
                    <span className="feedback__char-count">{comment.length}/1000</span>
                </div>

                {/* Error */}
                {error && (
                    <div className="feedback__error animate-fade-in">
                        ⚠️ {error}
                    </div>
                )}

                {/* Submit Button */}
                <button
                    className={`feedback__submit ${rating > 0 ? 'feedback__submit--ready' : ''}`}
                    onClick={handleSubmit}
                    disabled={submitting || rating === 0}
                >
                    {submitting ? (
                        <span className="feedback__submit-loading">
                            <span className="feedback__spinner" />
                            Sending...
                        </span>
                    ) : (
                        <>
                            <svg className="feedback__whatsapp-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                            </svg>
                            Submit & Send via WhatsApp
                        </>
                    )}
                </button>

                {/* Info Note */}
                <p className="feedback__info">
                    💡 After submitting, WhatsApp will open with your feedback pre-filled.
                    Just tap <strong>Send</strong> to deliver it to our team!
                </p>
            </div>
        </div>
    );
}


/**
 * Client-side fallback WhatsApp link generator
 * (used only if the backend call fails)
 */
function _buildWhatsAppLink(rating, comment, name) {
    const stars = '⭐'.repeat(rating) + '☆'.repeat(5 - rating);
    let msg = `📋 *Nexora — Student Feedback*\n\n⭐ *Rating:* ${stars} (${rating}/5)`;
    if (name) msg += `\n👤 *Student:* ${name}`;
    if (comment) msg += `\n💬 *Comment:* ${comment}`;
    msg += `\n\n— Sent from Nexora Study Assistant`;
    return `https://wa.me/${WHATSAPP_PHONE}?text=${encodeURIComponent(msg)}`;
}


export default Feedback;
