import inspect
import os
import time
import traceback
from collections import deque
from functools import wraps
from threading import Timer

from sims4.commands import Command, unregister

from wiggleton.helpers.native.decorator import decorator
from wiggleton.helpers.native.undecorated import undecorated

LOGGING_DELAY = 2
LOGGING_MAX_COUNT = 1000
logging_messages = deque()
logging_delay_timer = None
documents_path = os.path.dirname(os.path.realpath(__file__))
documents_path = documents_path[:documents_path.rindex('Mods') - 1]


def log(content):
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
    _log(documents_path, *contents)
    logging_delay_timer = None


LOG_FILE = 'wiggleton.log'


def _log(directory, *contents):
    with open(os.path.join(directory, LOG_FILE), 'a+') as stream:
        for content in contents:
            if not stream.closed:
                stream.write(content + '\n')


def log_method_call(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        module = inspect.getmodule(func)
        name = module.__name__ + '.' + func.__name__
        try:
            log(f'{name}: {locals()}')
            return func(*args, **kwargs)
        except Exception:
            log(f'Error while invoking {name}: {str(traceback.format_exc())}')

    return wrapper

@decorator
def create_injection_log(source, *args, **kwargs) -> object:
    results = None
    try:
        module = inspect.getmodule(source)
        output = module.__name__ + "." + source.__name__ + " | " + str(args) + " | " + str(kwargs)
        log(output)
        bound_args = inspect.signature(source).bind(*args, **kwargs)
        bound_args.apply_defaults()
        output = module.__name__ + "." + source.__name__ + " | " + str(bound_args)
        log(output)
        results = source(*args, **kwargs)
    except Exception as e:
        log('Injected Function Error (' + source.__name__ + '): {}'.format(e))
        log(str(traceback.format_exc()))
    return results


def create_command_log(command_name, command_type, function):
    log("Injecting = " + str(command_name) + " " + str(command_type))
    unregister(command_name)
    Command(command_name, command_type=command_type)(create_injection_log(undecorated(function)))


def create_injection_append(source, dest):

    def function_to_inject(*args, **kwargs):
        results = source(*args, **kwargs)
        try:
            dest(results, *args, **kwargs)
        except Exception as e:
            log('Injected Function Error (' + source.__name__ + '): {}'.format(e), force=True)
        return results

    return function_to_inject