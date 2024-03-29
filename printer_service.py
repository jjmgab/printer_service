import sys, os, shutil, getopt, time, Queue, threading, cups
from enum import Enum
from collections import deque

class LogType(Enum):
    SYSTEM = 1
    SERVICE = 2
    HELP = 3
    CONFIG = 4

def log(log_type, message):
    ltype = log_type._name_
    print '[' + ltype + ']: ' + message

def handle_args(argv):
    """
        Handle input arguments.
    """
    HELP_STRING = 'printer_service.py -t <time>'
    options = {'time': -1, 'verbose': False}
    try:
        opts, args = getopt.getopt(argv,'ht:v',['time=','verbose'])
    except getopt.GetoptError:
        log(LogType.HELP, HELP_STRING)
        sys.exit(2)

    # handle options
    for opt, arg in opts:
        if (opt == '-h'):
            # help
            log(LogType.HELP, HELP_STRING)
            sys.exit()
        elif (opt in ('-t', '--time')):
            # time
            if (not arg.isdecimal() or int(arg) < 1):
                options['time'] = 1
            else:
                options['time'] = int(arg)
        elif (opt in ('-v', '--verbose')):
            # verbose
            options['verbose'] = True

    return options

def check_path(path, verbose = False):
    """ 
        Check if given path exists. If not, create it.
    """
    if (not os.path.isdir(path)):
        if (verbose):
            log(LogType.SERVICE, 'No ' + path + '. Creating. . .')
        os.mkdir(path, 0o777)

def print_file(filepath):
    # getting printer params
    conn = cups.Connection()
    printers = conn.getPrinters()
    printer_name = printers.keys()[0]
    
    log(LogType.SERVICE, 'Printing file ' + filepath + ' with printer ' + printer_name)

    conn.printFile(printer_name, filepath, 'Python Automated Printing Task', {})

    os.remove(filepath)

def worker_printer():
    while True:
        item = tasks.get()
        if (item is None):
            break
        print_file(item)
        tasks.task_done()

if __name__ == "__main__":

    # config
    log(LogType.SERVICE, 'Initializing configuration. . .')
    options = handle_args(sys.argv[1:])
    
    CFG_VERBOSE = options['verbose']

    if (options['time'] > 0):
        CFG_TIME = options['time']
    else:
        CFG_TIME = 1
    if (CFG_VERBOSE):
        log(LogType.CONFIG, 'Loop time: ' + CFG_TIME + 's')

    log(LogType.SERVICE, 'Configuration finished!')

    # paths
    PATH_ORIGIN='//share//print//'
    PATH_QUEUE = PATH_ORIGIN + 'queue//'

    # check for path availability
    check_path(PATH_ORIGIN, CFG_VERBOSE)
    check_path(PATH_QUEUE, CFG_VERBOSE)

    # file queue
    files = deque([])

    # task queue
    tasks = Queue.Queue()

    # termination flag
    finalize = False

    # initializing printing thread
    thread_printer = threading.Thread(target=worker_printer)
    thread_printer.start()

    while not finalize:

        # preparing file queue
        for file in os.listdir(PATH_ORIGIN):
            if (os.path.isfile(PATH_ORIGIN + file)):
                # if terminate file exists in the origin dir, stop the service
                if (file == 'terminate'):
                    log(LogType.SERVICE, 'Stopping service. . .')
                    os.remove(PATH_ORIGIN + 'terminate')
                    finalize = True
                    break

                # add a file to the queue
                if (file[-4:] == '.pdf'):
                    if (CFG_VERBOSE):
                        log(LogType.SERVICE, 'New file: ' + file)
                    files.append(PATH_QUEUE + file)
                    os.rename(PATH_ORIGIN + file, PATH_QUEUE + file)

        if (not finalize):   
            # add file to queue
            for i in range(len(files)):
                item = files.popleft()
                if (CFG_VERBOSE):
                    log(LogType.SERVICE, 'Adding a file to printer queue: ' + item)
                tasks.put(item)
            
            # wait
            time.sleep(CFG_TIME)
    
    # terminate thread
    log(LogType.SERVICE, 'Terminating threads. . .')

    # block until all tasks are done
    if (CFG_VERBOSE):
        log(LogType.SERVICE, 'Waiting for all tasks to finish. . .')
    tasks.join()

    # stop workers
    if (CFG_VERBOSE):
        log(LogType.SERVICE, 'Stopping workers. . .')
    tasks.put(None)
    thread_printer.join()

    log(LogType.SERVICE, 'Threads terminated!')

    # cleanup; remove queue directory and all its content
    if (CFG_VERBOSE):
        log(LogType.SERVICE, 'Deleting remaining files. . .')
    shutil.rmtree(PATH_QUEUE)