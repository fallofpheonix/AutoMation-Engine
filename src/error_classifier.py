from enum import Enum


class ErrorType(str, Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class ErrorClassifier:
    def classify(self, error: str) -> ErrorType:
        e = error.lower()

        if any(x in e for x in ["timeout", "not found", "interrupted"]):
            return ErrorType.TEMPORARY

        if any(x in e for x in ["permission denied", "not installed", "invalid"]):
            return ErrorType.PERMANENT

        return ErrorType.UNKNOWN
