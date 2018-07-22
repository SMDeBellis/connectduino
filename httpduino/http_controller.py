#!/usr/bin/python

import httplib
from threading import Thread, Event
from Queue import Queue
import logging
from time import sleep
from sys import platform
from os import path, makedirs
######################Logging setup##########################################

log = logging.getLogger('http_controller_module')
log.setLevel(logging.INFO)

#create a file handler
if 'win' in platform:
    log_dir = 'C:\ProgramData\connectduino\logs\\'
else:
    log_dir = '/var/log/connectduino/'

if not path.exists(log_dir):
    makedirs(log_dir)

file_name = 'httpduino.log'

handler = logging.FileHandler(path.join(log_dir, file_name))
handler.setLevel(logging.INFO)

#create a Logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

#add the handlers to the Logger
log.addHandler(handler)

class HttpController:
    def __init__(self, queue):
        self.shutdown_event = Event()
        self.connection_listener = HttpConnectionListener(18200, queue, self.shutdown_event)
        self.log = logging.getLogger('http_controller_module.HttpController')

    def shutdown(self):
        self.shutdown_event.set()
        while self.shutdown_event.is_set():
            pass


class HttpConnectionListener(Thread):
    def __init__(self, listening_port, queue, shutdown_event):
        self.log = logging.getLogger('http_controller_module.HttpConnectionListener')
        self.port = listening_port # port to listen on for new connections
        self.available_ports = [x for x in range(18201, 18300)]
        self.shutdown_event = shutdown_event
        self.queue = queue
        self.connections = {} #maps ports to events

    def run(self):
        pass

    def shutdown_listeners(self):
        for port, event in self.connections.iteritems():
            event.set()

        while len(self.connections) > 0:
            self.remove_dead_connections()

        self.shutdown_event.clear()

    def remove_dead_connections(self):
        dead_ports = []
        for port, event in self.connections.iteritems():
            if event.is_set():
                dead_ports.append(port)
        for port in dead_ports:
            del self.connections[port]
            self.available_ports.append(port)


class HttpListener(Thread):
    def __init__(self, port, queue):
        self.log = logging.getLogger('http_controller_module.HttpListener')
        self.port = port
        self.queue = queue

    def run(self):
        pass


if __name__ == '__main__':
    def analyze_queue(data_list):
        for i, data in enumerate(sorted(data_list)):
            if i != data:
                return False
        return True

    log.info('\n\n#######################Starting up Server############################')
    queue = Queue()

    log.info('creating connection_listener')
    connection_listener = HttpController(queue)
    nums = []
    try:
        while True:
            try:
                #log.debug('getting value')
                val = queue.get(timeout=.05)
                queue.task_done()
                #log.debug('done getting value')
            except Empty:
                log.debug("queue empty on get call") # noisy logging
                pass
            else:
                try:
                    nums.append(int(val))
                    #log.info('value received = ' + str(val))
                #queue.task_done()
                except:
                    pass
    except KeyboardInterrupt:
        log.info('Keyboard interrupt received. Shutting down connection listener')
        log.info('length of array = ' + str(len(nums)))
        log.info(str(sorted(nums)))
        log.info('All present: ' + str(analyze_queue(nums)))
        connection_listener.shutdown()
        log.info()
        log.info('Shutting down main')