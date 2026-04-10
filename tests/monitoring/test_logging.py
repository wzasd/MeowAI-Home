"""Structured logging tests"""
import pytest
import json
import io
import logging
from src.monitoring.logging import StructuredLogger, get_logger, JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_format_includes_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        record.key = "value"
        record.user_id = "123"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "test message"
        assert data["key"] == "value"
        assert data["user_id"] == "123"

    def test_format_excludes_standard_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        # Should only have timestamp, level, logger, message
        assert "pathname" not in data
        assert "lineno" not in data
        assert "module" not in data

    def test_format_with_exception(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except Exception:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0,
                msg="error occurred", args=(), exc_info=exc_info
            )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "test error" in data["exception"]


class TestStructuredLogger:
    def test_logger_creation(self):
        logger = StructuredLogger("test")
        assert logger.name == "test"

    def test_log_info(self, caplog):
        # Set up JSON formatter for the logger
        handler = logging.StreamHandler(caplog.handler.stream)
        handler.setFormatter(JSONFormatter())
        test_logger = logging.getLogger("test_info")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.INFO)

        logger = StructuredLogger("test_info")
        logger._logger = test_logger

        with caplog.at_level(logging.INFO):
            logger.info("test message", key="value")

        assert "test message" in caplog.text
        assert "key" in caplog.text

    def test_log_with_extra_fields(self, caplog):
        handler = logging.StreamHandler(caplog.handler.stream)
        handler.setFormatter(JSONFormatter())
        test_logger = logging.getLogger("test_extra")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.INFO)

        logger = StructuredLogger("test_extra")
        logger._logger = test_logger

        with caplog.at_level(logging.INFO):
            logger.info("action", user_id="123", action="login", status="success")

        assert "user_id" in caplog.text
        assert "action" in caplog.text

    def test_log_error(self, caplog):
        handler = logging.StreamHandler(caplog.handler.stream)
        handler.setFormatter(JSONFormatter())
        test_logger = logging.getLogger("test_error")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.ERROR)

        logger = StructuredLogger("test_error")
        logger._logger = test_logger

        with caplog.at_level(logging.ERROR):
            logger.error("error occurred", error_code=500)

        assert "error occurred" in caplog.text
        assert "error_code" in caplog.text

    def test_log_exception(self, caplog):
        handler = logging.StreamHandler(caplog.handler.stream)
        handler.setFormatter(JSONFormatter())
        test_logger = logging.getLogger("test_exc")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.ERROR)

        logger = StructuredLogger("test_exc")
        logger._logger = test_logger

        try:
            raise ValueError("test error")
        except Exception:
            with caplog.at_level(logging.ERROR):
                logger.exception("caught exception")

        assert "test error" in caplog.text


class TestGetLogger:
    def test_get_logger_singleton(self):
        logger1 = get_logger("singleton")
        logger2 = get_logger("singleton")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        logger1 = get_logger("name1")
        logger2 = get_logger("name2")
        assert logger1.name == "name1"
        assert logger2.name == "name2"


class TestSetupLogging:
    def test_setup_logging_json_output(self):
        stream = io.StringIO()
        setup_logging(level=logging.INFO, json_output=True, stream=stream)

        test_logger = logging.getLogger("setup_test_json")
        test_logger.info("json test message", extra={"extra_field": "value"})

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["message"] == "json test message"
        assert data["extra_field"] == "value"

    def test_setup_logging_plain_output(self):
        stream = io.StringIO()
        setup_logging(level=logging.INFO, json_output=False, stream=stream)

        test_logger = logging.getLogger("setup_test_plain")
        test_logger.info("plain test message")

        output = stream.getvalue()
        assert "plain test message" in output
        assert "INFO" in output
