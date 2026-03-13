"""
Core exceptions for Nexora Study Assistant.
Provides structured error handling across all modules.
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)


class SubjectNotFoundError(AppException):
    """Raised when a subject code is not found."""
    def __init__(self, subject_code: str):
        super().__init__(
            detail=f"Subject '{subject_code}' not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnitNotFoundError(AppException):
    """Raised when a unit number is invalid for a subject."""
    def __init__(self, subject_code: str, unit_number: int):
        super().__init__(
            detail=f"Unit {unit_number} not found in subject '{subject_code}'.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class DocumentProcessingError(AppException):
    """Raised when document processing fails."""
    def __init__(self, detail: str = "Failed to process document."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class RAGError(AppException):
    """Raised when the RAG pipeline encounters an error."""
    def __init__(self, detail: str = "RAG system error."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LLMError(AppException):
    """Raised when LLM interaction fails."""
    def __init__(self, detail: str = "LLM service error."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class MemoryError(AppException):
    """Raised when the memory system encounters an error."""
    def __init__(self, detail: str = "Memory system error."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ChatNotFoundError(AppException):
    """Raised when a chat session is not found."""
    def __init__(self, chat_id: str):
        super().__init__(
            detail=f"Chat session '{chat_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )
