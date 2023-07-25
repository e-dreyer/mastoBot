import logging

__all__ = ["mastoBot", "configManager"]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-20s - [%(levelname)s] - %(module)s.%(funcName)-20s - %(message)-30s",
)

# File logger
file_logger = logging.FileHandler("app.log", "w")
file_logger.setLevel(logging.INFO)
file_logger.setFormatter(
    logging.Formatter(
        "%(asctime)-20s - [%(levelname)s] - %(module)s.%(funcName)-20s - %(message)-30s"
    )
)

# Get the root logger
root_logger = logging.getLogger()
root_logger.addHandler(file_logger)
