import logging
import os

# Configure logging to both file and console
log_file = "imp.log"

# Clear log on startup (Disabled to preserve crash info)
# if os.path.exists(log_file):
#     try:
#         os.remove(log_file)
#     except:
#         pass

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
