from enum import Enum


class FileSource(Enum):
    """Enumeration of valid sources"""

    WEB = "WEB"
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    KNOWLEDGE = "KNOWLEDGE"
    OTHER = "OTHER"


class FileStatus(Enum):
    """Enumeration of valid File Status"""

    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOAD_SUCCESS = "UPLOAD_SUCCESS"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    PROCESSING = "PROCESSING"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    SUCCESS = "SUCCESS"


file_source_choices = tuple([source.value for source in FileSource])
file_status_choices = tuple([status.value for status in FileStatus])
