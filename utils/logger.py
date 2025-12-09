import logging
import os
from datetime import datetime

def setup_logger(name="github_scanner"):
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"scan_{timestamp}.log")

    # Configure Root Logger
    logger = logging.getLogger() 
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates if called multiple times
    if logger.handlers:
        logger.handlers = []

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)

    return logging.getLogger(name)
