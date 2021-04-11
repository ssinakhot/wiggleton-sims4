import os
LOG_FILE = 'wiggleton.log'

def log(directory, *contents):
    with open(os.path.join(directory, LOG_FILE), 'a+') as stream:
        for content in contents:
            if not stream.closed:
                stream.write(content + '\n')

