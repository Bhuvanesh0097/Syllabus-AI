/**
 * useChat Hook — manages chat state, session initialization with greeting,
 * message sending, and conversation history.
 */

import { useState, useCallback, useRef } from 'react';
import api from '../api/client';

function useChat() {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [chatId, setChatId] = useState(null);
    const [error, setError] = useState(null);
    const [sessionStarted, setSessionStarted] = useState(false);
    const [lastContextSwitch, setLastContextSwitch] = useState(null);
    const initializingRef = useRef(false);

    /**
     * Start a new study session — calls the backend to generate
     * a personalized AI greeting with unit overview.
     */
    const startSession = useCallback(async (studentInfo) => {
        // Prevent duplicate initialization
        if (initializingRef.current) return;
        initializingRef.current = true;

        setIsLoading(true);
        setError(null);
        setLastContextSwitch(null);

        try {
            const response = await api.startSession(studentInfo);

            setChatId(response.chat_id);
            setMessages([
                {
                    role: 'assistant',
                    content: response.greeting,
                    timestamp: new Date().toISOString(),
                    isGreeting: true,
                },
            ]);
            setSessionStarted(true);
        } catch (err) {
            console.error('Failed to start session:', err);
            setError(err.message);

            // Provide a local fallback greeting if backend fails
            const subjectName = studentInfo.subject || studentInfo.subjectCode || 'your subject';
            const unitNum = studentInfo.unit || studentInfo.unitNumber || '?';

            setMessages([
                {
                    role: 'assistant',
                    content: `Hello ${studentInfo.name} 👋\n\nWelcome to your study session!\n\n**📚 Subject:** ${subjectName}\n**📋 Unit:** Unit ${unitNum}\n\nI'm your AI Study Assistant. I'm currently having trouble connecting to the AI service — please make sure the **Gemini API Key** is configured in the backend \`.env\` file.\n\nOnce connected, I'll be able to:\n- 📝 Help you prepare for 2-mark and 10-mark questions\n- 💡 Explain concepts clearly\n- 📋 Create quick revision summaries\n\nTry sending me a message! 🎯`,
                    timestamp: new Date().toISOString(),
                    isGreeting: true,
                },
            ]);
            setSessionStarted(true);
        } finally {
            setIsLoading(false);
            initializingRef.current = false;
        }
    }, []);

    /**
     * Send a message in the current chat session.
     */
    const sendMessage = useCallback(
        async (content, options = {}) => {
            if (!content.trim() || isLoading) return;

            setError(null);

            // Add user message to the UI immediately
            const userMsg = {
                role: 'user',
                content: content.trim(),
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, userMsg]);
            setIsLoading(true);

            try {
                const response = await api.sendMessage(content.trim(), {
                    subjectCode: options.subjectCode,
                    unitNumber: options.unitNumber,
                    section: options.section,
                    answerStyle: options.answerStyle,
                    chatId: chatId,
                    tone: options.tone,
                });

                // Update chat ID if this created a new session
                if (response.chat_id) {
                    setChatId(response.chat_id);
                }

                // Check for context switch
                if (response.context_switch) {
                    setLastContextSwitch(response.context_switch);
                }

                // Add AI response
                const aiMsg = {
                    role: 'assistant',
                    content: response.message,
                    timestamp: new Date().toISOString(),
                    sources: response.sources || [],
                    contextSwitch: response.context_switch || null,
                    quality: response.quality || null,
                };
                setMessages((prev) => [...prev, aiMsg]);
            } catch (err) {
                console.error('Send message error:', err);
                setError(err.message);

                // Add error message to chat
                setMessages((prev) => [
                    ...prev,
                    {
                        role: 'assistant',
                        content: `⚠️ Sorry, I encountered an error: ${err.message}\n\nPlease try again or check that the backend is running.`,
                        timestamp: new Date().toISOString(),
                        isError: true,
                    },
                ]);
            } finally {
                setIsLoading(false);
            }
        },
        [chatId, isLoading]
    );

    /**
     * Clear the current chat and reset state.
     */
    const clearChat = useCallback(() => {
        setMessages([]);
        setChatId(null);
        setError(null);
        setSessionStarted(false);
        setLastContextSwitch(null);
        initializingRef.current = false;
    }, []);

    /**
     * Load an existing chat session by ID.
     */
    const loadChat = useCallback(async (existingChatId) => {
        setIsLoading(true);
        try {
            const response = await api.getChatSession(existingChatId);
            if (response.session) {
                setChatId(existingChatId);
                setMessages(
                    response.session.messages.map((m) => ({
                        role: m.role,
                        content: m.content,
                        timestamp: m.timestamp,
                    }))
                );
                setSessionStarted(true);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    return {
        messages,
        isLoading,
        chatId,
        error,
        sessionStarted,
        lastContextSwitch,
        startSession,
        sendMessage,
        clearChat,
        loadChat,
    };
}

export default useChat;
