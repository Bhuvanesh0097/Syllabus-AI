/**
 * ChatMessage Component — displays user and AI messages with markdown rendering.
 * Converts markdown syntax to HTML for rich display (headings, bold, lists, code blocks).
 */

import { useMemo } from 'react';
import './ChatMessage.css';

/**
 * Simple markdown-to-HTML converter.
 * Handles: headings, bold, italic, bullet lists, numbered lists,
 * inline code, code blocks, blockquotes, and links.
 */
function renderMarkdown(text) {
    if (!text) return '';

    let html = text;

    // Escape HTML entities (safety)
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Code blocks (```) — must be before inline processing
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre class="chat-code-block"><code class="lang-${lang || 'text'}">${code.trim()}</code></pre>`;
    });

    // Inline code (`)
    html = html.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');

    // Headings
    html = html.replace(/^#### (.+)$/gm, '<h4 class="chat-h4">$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3 class="chat-h3">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 class="chat-h2">$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 class="chat-h1">$1</h1>');

    // Bold + italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="chat-blockquote">$1</blockquote>');

    // Horizontal rule
    html = html.replace(/^---$/gm, '<hr class="chat-hr" />');

    // Unordered lists (- or *)
    html = html.replace(/^[\-\*] (.+)$/gm, '<li class="chat-li">$1</li>');
    html = html.replace(/((?:<li class="chat-li">.*<\/li>\n?)+)/g, '<ul class="chat-ul">$1</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li class="chat-li-ordered">$1</li>');
    html = html.replace(/((?:<li class="chat-li-ordered">.*<\/li>\n?)+)/g, '<ol class="chat-ol">$1</ol>');

    // Paragraphs — wrap standalone lines in <p> tags
    html = html.replace(/^(?!<[a-z])(.*\S.*)$/gm, (match) => {
        // Don't wrap if it's already an HTML element
        if (/^</.test(match)) return match;
        return `<p class="chat-p">${match}</p>`;
    });

    // Clean up extra newlines
    html = html.replace(/\n{3,}/g, '\n\n');

    return html;
}


function ChatMessage({ message, isLast }) {
    const isUser = message.role === 'user';
    const isError = message.isError;
    const isGreeting = message.isGreeting;

    // Memoize markdown rendering for performance
    const renderedHtml = useMemo(() => {
        if (isUser) return null; // User messages are plain text
        return renderMarkdown(message.content);
    }, [message.content, isUser]);

    return (
        <div
            className={`chat-msg ${isUser ? 'chat-msg--user' : 'chat-msg--ai'} ${isError ? 'chat-msg--error' : ''} ${isGreeting ? 'chat-msg--greeting' : ''} ${isLast ? 'animate-fade-in-up' : ''}`}
        >
            <div className="chat-msg__avatar">
                {isUser ? '👤' : <img src="/nexora-logo.png" alt="Nexora" className="chat-msg__avatar-logo" />}
            </div>

            <div className="chat-msg__content">
                <div className="chat-msg__header">
                    <span className="chat-msg__sender">
                        {isUser ? 'You' : 'Nexora'}
                    </span>
                    <span className="chat-msg__time">
                        {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                        })}
                    </span>
                </div>

            {isUser ? (
                    <div className="chat-msg__body">{message.content}</div>
                ) : (
                    <div
                        className="chat-msg__body chat-msg__markdown"
                        dangerouslySetInnerHTML={{ __html: renderedHtml }}
                    />
                )}

                {/* RAG Images — extracted from uploaded PDFs, NEVER AI-generated */}
                {!isUser && message.images && message.images.length > 0 && (
                    <div className="chat-msg__images">
                        <div className="chat-msg__images-label">
                            📎 Diagrams from your notes
                        </div>
                        <div className="chat-msg__images-grid">
                            {message.images.map((img, i) => (
                                <div key={i} className="chat-msg__image-card">
                                    <img
                                        src={img.url || img.public_url}
                                        alt={img.caption || 'Diagram from notes'}
                                        className="chat-msg__image"
                                        loading="lazy"
                                        onClick={() => window.open(img.url || img.public_url, '_blank')}
                                    />
                                    {img.caption && (
                                        <p className="chat-msg__image-caption">{img.caption}</p>
                                    )}
                                    {img.source_file && (
                                        <span className="chat-msg__image-source">
                                            📄 {img.source_file}
                                            {img.page_number != null && ` • Page ${img.page_number + 1}`}
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {message.sources && message.sources.length > 0 && (
                    <div className="chat-msg__sources">
                        <span className="chat-msg__sources-label">Sources:</span>
                        {message.sources.map((src, i) => (
                            <span key={i} className="badge badge-accent">{src}</span>
                        ))}
                    </div>
                )}


            </div>
        </div>
    );
}

export default ChatMessage;
