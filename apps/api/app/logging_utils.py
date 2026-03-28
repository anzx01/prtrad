import logging
from typing import Any


class ServiceContextFilter(logging.Filter):
    def __init__(self, service: str, environment: str, rule_version: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment
        self.rule_version = rule_version

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        record.environment = self.environment
        record.rule_version = self.rule_version
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "task_id"):
            record.task_id = "-"
        return True


def configure_logging(service: str, environment: str, rule_version: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(service)s] env=%(environment)s "
            "req=%(request_id)s task=%(task_id)s rule=%(rule_version)s %(message)s"
        )
    )
    handler.addFilter(ServiceContextFilter(service, environment, rule_version))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def bind_log_context(logger: logging.Logger, **extra: Any) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logger, extra)

