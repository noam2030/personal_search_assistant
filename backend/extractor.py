"""
Backwards-compatibility stub for backend.extractor.
Moved to backend.agent.extract_content_agent.
"""
from backend.agent.extract_content_agent import (
    extract_content,
    _call_gemini_with_retry,
)

__all__ = ["extract_content", "_call_gemini_with_retry"]
