"""Production logging configuration for LeadOps engine and agent workflows."""

import logging
import os
import sys

# Configure standard root logger
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

log_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "leadops.log")

# Create file handler and console handler
file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
file_handler.setLevel(logging.INFO)

class SafeConsoleStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
                self.flush()
            except UnicodeEncodeError:
                safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
                stream.write(safe_msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)

console_handler = SafeConsoleStreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
console_handler.setLevel(logging.INFO)

root_logger = logging.getLogger("leadops")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
root_logger.propagate = False


def get_logger(component_name: str) -> logging.Logger:
    """Return a scoped logger for a specific engine component."""
    return logging.getLogger(f"leadops.{component_name}")
