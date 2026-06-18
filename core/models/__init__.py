"""Core app models, grouped by domain.

All models are re-exported here so imports stay stable:
    from core.models import Participant, Certificate, Event
"""
from .catalogs import FACULTY_CHOICES, Faculty, AcademicTitle
from .users import User, AccessRequest
from .signatures import Signature, GlobalDesign
from .participants import Participant, ParticipantToken, PasswordResetToken
from .certificates import CertificateBatch, Certificate
from .events import Event, Speaker, Attendance, Enrollment
from .summaries import SessionSummary, ProcessingStatus, QuizAttempt
from .audit import AuditLog, AuditAction
from .integrations import GoogleCredential, AIConfig, AIProvider, PROVIDER_MODELS
from .design_system import UIDesignTokens

__all__ = [
    'FACULTY_CHOICES',
    'Faculty',
    'AcademicTitle',
    'User',
    'AccessRequest',
    'Signature',
    'GlobalDesign',
    'Participant',
    'ParticipantToken',
    'PasswordResetToken',
    'CertificateBatch',
    'Certificate',
    'Event',
    'Speaker',
    'Attendance',
    'Enrollment',
    'SessionSummary',
    'ProcessingStatus',
    'QuizAttempt',
    'AuditLog',
    'AuditAction',
    'GoogleCredential',
    'AIConfig',
    'AIProvider',
    'PROVIDER_MODELS',
    'UIDesignTokens',
]
