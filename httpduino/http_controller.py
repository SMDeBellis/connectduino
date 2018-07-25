#!/usr/bin/python

from socket import *
from threading import Thread, Event
from Queue import Queue, Empty, Full
import logging
from time import sleep
from sys import platform
from os import path, makedirs

# #####################Logging setup##########################################
log = logging.getLogger('http_controller_module')
log.setLevel(logging.INFO)

# create a file handler
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
        self.shutdown_event = shutdown_event
        self.queue = queue
        self.connections = {} #maps ports to events
        self.connection_events = {}

    def run(self):
        host = ''
        listener = socket(AF_INET, SOCK_STREAM)
        try:
            listener.bind((host, self.port))
            listener.listen(5)
        except:
            self.log.exception('exception thrown while binding to listening socket at port ' + self.port)

        try:
            while not self.shutdown_event.is_set():
                (clientsocket, address) = listener.accept()
                self.connection_events[address] = Event()
                self.connections[address] = HttpListener(address, clientsocket, self.queue, self.connection_events[address])
        except:
            self.log.exception('exception thrown while listening to new connections')
        finally:
            self.shutdown_listeners()

    def shutdown_listeners(self):
        for address, event in self.connection_events.iteritems():
            event.set()

        while len(self.connections) > 0:
            dead_connections = []
            for address, event in self.connection_events.iteritems():
                if not event.is_set():
                    dead_connections.append(address)
            for addr in dead_connections:
                del self.connections[addr]
                del self.connection_events[addr]

        self.shutdown_event.clear()

    def remove_dead_connections(self):
        dead_ports = []
        for addr, event in self.connection_events.iteritems():
            if event.is_set():
                dead_ports.append(addr)
        for addr in dead_ports:
            del self.connections[addr]
            del self.connection_events[addr]


class HttpListener(Thread):
    def __init__(self, addr, socket, queue, event):
        self.log = logging.getLogger('http_controller_module.HttpListener')
        self.addr = addr
        self.queue = queue
        self.socket = socket
        self.shutdown_event = event

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
                # log.debug('getting value')
                val = queue.get(timeout=.05)
                queue.task_done()
                # log.debug('done getting value')
            except Empty:
                log.debug("queue empty on get call") # noisy logging
                pass
            else:
                try:
                    nums.append(int(val))
                    #log.info('value received = ' + str(val))
                # queue.task_done()
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