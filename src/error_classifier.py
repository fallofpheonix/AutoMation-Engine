from enum import Enum


class ErrorType(Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """Classifies errors as temporary (retry) or permanent (don't retry)"""
    
    TEMPORARY_KEYWORDS = [
        "not found",
        "timeout",
        "interrupted",
        "try again",
        "busy",
        "loading",
        "connection",
        "network",
        "transient"
    ]
    
    PERMANENT_KEYWORDS = [
        "not installed",
        "permission denied",
        "permission error",
        "invalid",
        "syntax",
        "not implemented",
        "requires windows",
        "access denied"
    ]
    
    def classify(self, error_message: str) -> ErrorType:
        """
        Classify error as temporary or permanent
        
        Args:
            error_message: Error message to classify
            
        Returns:
            ErrorType enum (TEMPORARY, PERMANENT, or UNKNOWN)
        """
        if not error_message:
            return ErrorType.UNKNOWN
        
        error_lower = error_message.lower()
        
        # Check permanent first (more important)
        for keyword in self.PERMANENT_KEYWORDS:
            if keyword in error_lower:
                return ErrorType.PERMANENT
        
        # Then check temporary
        for keyword in self.TEMPORARY_KEYWORDS:
            if keyword in error_lower:
                return ErrorType.TEMPORARY
        
        # Default: treat as temporary (safer to retry than give up)
        return ErrorType.UNKNOWN
