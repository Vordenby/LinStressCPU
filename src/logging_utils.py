import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def _build_run_log_path(logs_dir: Path, timestamp: str) -> Path:
    log_path = logs_dir / f"{timestamp}.log"
    counter = 1
    while log_path.exists():
        log_path = logs_dir / f"{timestamp}_{counter}.log"
        counter += 1
    return log_path


def configure_application_logging(app_name: str = "linstress", base_dir: Optional[str] = None, level: int = logging.INFO):
    configured_logs_dir = os.environ.get("LINSTRESS_LOG_DIR")
    if configured_logs_dir:
        logs_dir = Path(configured_logs_dir).expanduser()
    else:
        base_path = Path(base_dir or os.path.dirname(os.path.abspath(__file__)))
        logs_dir = base_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    latest_path = logs_dir / "latest_log.log"
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_log_path = _build_run_log_path(logs_dir, run_timestamp)

    latest_path.touch(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        if getattr(handler, "_linstress_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(run_log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    file_handler._linstress_handler = True
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    stream_handler._linstress_handler = True
    root_logger.addHandler(stream_handler)

    logger = logging.getLogger(app_name)
    logger.setLevel(level)
    logger.propagate = True
    logger._linstress_run_timestamp = run_timestamp
    logger._linstress_run_log_path = run_log_path
    logger._linstress_latest_path = latest_path
    logger._linstress_archived = False
    logger._linstress_logs_dir = logs_dir

    return logger


def close_application_logging(logger: logging.Logger) -> Optional[Path]:
    if getattr(logger, "_linstress_archived", False):
        return None

    latest_path = getattr(logger, "_linstress_latest_path", None)
    run_log_path = getattr(logger, "_linstress_run_log_path", None)

    root_logger = logging.getLogger()
    handlers = [handler for handler in list(root_logger.handlers) if getattr(handler, "_linstress_handler", False)]
    for handler in handlers:
        root_logger.removeHandler(handler)
        handler.flush()
        handler.close()

    if latest_path and run_log_path and Path(run_log_path).exists():
        shutil.copyfile(run_log_path, latest_path)

    logger._linstress_archived = True
    return run_log_path


def _self_test() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = configure_application_logging(app_name="linstress", base_dir=tmpdir)
        logger.info("first run")
        close_application_logging(logger)

        logs_dir = Path(tmpdir) / "logs"
        latest_path = logs_dir / "latest_log.log"
        archived_logs = [name for name in os.listdir(logs_dir) if name != "latest_log.log"]
        assert latest_path.exists(), "latest_log should exist"
        assert len(archived_logs) == 1, "one timestamped file should be created"

        logger2 = configure_application_logging(app_name="linstress", base_dir=tmpdir)
        logger2.info("second run")
        close_application_logging(logger2)

        updated_logs = [name for name in os.listdir(logs_dir) if name != "latest_log.log"]
        assert len(updated_logs) == 2, "a new timestamped file should be created for each run"


if __name__ == "__main__":
    _self_test()
