import io
import logging
import sys

from pydantic import SecretStr

from src.core.log_config import SecretMaskingProcessor


def test_pydantic_secret_masking_direct():
    """Verify that Pydantic SecretStr objects are masked when passed directly to redact_any."""
    processor = SecretMaskingProcessor()
    secret = SecretStr("top_secret_value")

    # Even if not in processor.secrets, it should be masked because it has get_secret_value
    assert processor.redact_any(secret) == "[MASKED]"


def test_logging_traceback_redaction():
    """Verify that standard logging redacts secrets from tracebacks and stack traces."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_traceback")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    processor = SecretMaskingProcessor()
    secret_val = "sensitive_traceback_info"
    processor.secrets.add(secret_val)
    logger.addFilter(processor)

    try:
        raise ValueError(f"Error with {secret_val}")
    except ValueError:
        logger.exception("An error occurred")

    output = stream.getvalue()
    assert secret_val not in output
    assert "[MASKED]" in output
    # Ensure it's in the traceback area
    assert "ValueError: Error with [MASKED]" in output


def test_logging_stack_info_redaction():
    """Verify that standard logging redacts secrets from stack_info."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_stack")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    processor = SecretMaskingProcessor()
    secret_val = "sensitive_stack_info"
    processor.secrets.add(secret_val)
    logger.addFilter(processor)

    # Simulate stack info containing the secret
    record = logger.makeRecord("name", logging.INFO, "fn", 1, f"msg with {secret_val}", None, None)
    record.stack_info = f"Stack trace containing {secret_val}"

    processor.filter(record)

    assert secret_val not in record.msg
    assert secret_val not in record.stack_info
    assert "[MASKED]" in record.msg
    assert "[MASKED]" in record.stack_info


def test_structlog_traceback_redaction():
    """Verify that the masking processor works with structlog's event_dict after format_exc_info."""
    processor = SecretMaskingProcessor()
    secret_val = "sensitive_structlog_info"
    processor.secrets.add(secret_val)

    # After format_exc_info, the exception string is in the 'exception' key
    event_dict = {"event": "failure", "exception": f"Traceback...\nValueError: {secret_val}"}

    redacted = processor(None, "error", event_dict)

    assert secret_val not in redacted["exception"]
    assert "[MASKED]" in redacted["exception"]


def test_proactive_exc_info_formatting():
    """Verify that Filter proactively formats and redacts exc_info if exc_text is missing."""
    processor = SecretMaskingProcessor()
    secret_val = "proactive_secret"
    processor.secrets.add(secret_val)

    try:
        raise ValueError(f"Panic with {secret_val}")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="p",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=sys.exc_info(),
        )

    assert not hasattr(record, "exc_text") or record.exc_text is None

    processor.filter(record)

    assert hasattr(record, "exc_text")
    assert secret_val not in record.exc_text
    assert "[MASKED]" in record.exc_text
