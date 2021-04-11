import os
import time
from collections import deque
from threading import Timer
from wiggleton.helpers.logger import log
LOGGING_DELAY = 1
LOGGING_MAX_COUNT = 1000
logging_messages = deque()
logging_delay_timer = None
documents_path = os.path.dirname(os.path.realpath(__file__))
documents_path = documents_path[:documents_path.rindex('Mods') - 1]


def wiggleton_log(content):
    global logging_delay_timer
    logging_messages.append('[' + time.strftime('%Y/%m/%d %H:%M:%S') + '] ' + str(content))
    if logging_delay_timer is None:
        logging_delay_timer = Timer(LOGGING_DELAY, consume_logging_messages)
        logging_delay_timer.daemon = False
        logging_delay_timer.start()


def consume_logging_messages():
    global logging_delay_timer
    contents = []
    for _ in range(LOGGING_MAX_COUNT):
        try:
            contents.append(logging_messages.popleft())
        except IndexError:
            break
    log(documents_path, *contents)
    logging_delay_timer = None

