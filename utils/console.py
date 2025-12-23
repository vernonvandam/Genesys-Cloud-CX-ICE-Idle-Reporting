import sys

class termcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    YELLOW = '\033[33m'

def ok(*args, **kwargs):
    print(termcolors.OKGREEN, 'ok:', *args, file=sys.stderr, end=termcolors.ENDC+'\n', **kwargs)

def info(*args, **kwargs):
    print(termcolors.OKBLUE, 'info:', *args, file=sys.stderr, end=termcolors.ENDC+'\n', **kwargs)

def warn(*args, **kwargs):
    print(termcolors.WARNING, 'warn:', *args, file=sys.stderr, end=termcolors.ENDC+'\n', **kwargs)

def fail(*args, **kwargs):
    print(termcolors.FAIL, 'error:', *args, file=sys.stderr, end=termcolors.ENDC+'\n', **kwargs)
