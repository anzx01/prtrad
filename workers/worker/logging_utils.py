import logging

from worker.config import settings


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [worker] env=%(environment)s "
            "task=%(task_id)s rule=%(rule_version)s %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root_logger.addHandler(handler)

    class ContextFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.environment = settings.app_env
            record.rule_version = settings.rule_version
            if not hasattr(record, "task_id"):
                record.task_id = "-"
            return True

    handler.addFilter(ContextFilter())

