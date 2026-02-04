"""Utility functions."""

from .cache import ResponseCache, get_cache
from .content import extract_content
from .files import FileInfo, FileStorage, get_file_storage
from .health import CLIStatus, check_all_clis, check_cli_available, log_cli_status
from .metrics import MetricsCollector, RequestMetrics, get_metrics
from .queue import QueueStats, RequestQueue, get_request_queue
from .retry import RetryError, is_retryable, retry_async, with_retry
from .sessions import Session, SessionManager, get_session_manager
from .subprocess import create_subprocess, get_sandbox_dir, is_windows, needs_shell
from .summarize import (
    apply_summary_to_messages,
    generate_summary,
    get_messages_to_summarize,
    needs_summarization,
)
from .tokens import TokenCounter, count_message_tokens, count_tokens, get_token_counter
from .tools import (
    create_tool_system_prompt,
    format_tool_calls_response,
    format_tool_results_for_prompt,
    has_tool_calls,
    parse_tool_calls,
    prepare_messages_for_cli,
)


__all__ = [
    # Health checks
    "check_cli_available",
    "check_all_clis",
    "log_cli_status",
    "CLIStatus",
    # Retry
    "retry_async",
    "with_retry",
    "RetryError",
    "is_retryable",
    # Metrics
    "get_metrics",
    "MetricsCollector",
    "RequestMetrics",
    # Cache
    "get_cache",
    "ResponseCache",
    # Token counting
    "get_token_counter",
    "count_tokens",
    "count_message_tokens",
    "TokenCounter",
    # Subprocess
    "create_subprocess",
    "is_windows",
    "needs_shell",
    "get_sandbox_dir",
    # File storage
    "get_file_storage",
    "FileStorage",
    "FileInfo",
    # Sessions
    "get_session_manager",
    "SessionManager",
    "Session",
    # Content extraction
    "extract_content",
    # Request queue
    "get_request_queue",
    "RequestQueue",
    "QueueStats",
    # Tools
    "create_tool_system_prompt",
    "parse_tool_calls",
    "format_tool_calls_response",
    "has_tool_calls",
    "format_tool_results_for_prompt",
    "prepare_messages_for_cli",
    # Summarization
    "generate_summary",
    "needs_summarization",
    "apply_summary_to_messages",
    "get_messages_to_summarize",
]
