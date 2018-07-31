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
log.setLevel(logging.DEBUG)

# create a file handler
if 'win' in platform:
    log_dir = 'C:\ProgramData\connectduino\logs\\'
else:
    log_dir = '/var/log/connectduino/'

if not path.exists(log_dir):
    makedirs(log_dir)

file_name = 'httpduino.log'

handler = logging.FileHandler(path.join(log_dir, file_name))
handler.setLevel(logging.DEBUG)

#create a Logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

#add the handlers to the Logger
log.addHandler(handler)

class HttpController:
    def __init__(self, a_queue):
        self.log = logging.getLogger('http_controller_module.HttpController')
        self.log.debug('creating httpcontroller')
        self.shutdown_event = Event()
        self.connection_listener = HttpConnectionListener(18200, a_queue, self.shutdown_event)
        self.connection_listener.start()
        self.connection_listener = None

    def wait_for_shutdown(self):

        self.shutdown_event.set()
        while self.shutdown_event.is_set():
            try:
                self.log.debug('waiting for shutdown')
                sleep(2)
            except:
                self.log.exception('exception thrown while waiting for HttpConnectionListener to shutdown.')
                self.shutdown_event.clear()
        self.log.debug("exiting shutdown()")

    def shutdown(self):
        # self.wait_for_shutdown()
        self.shutdown_event.set()
        self.log.debug("in shutdown() self.shutdown_event = " + str(self.shutdown_event.is_set()))
        while self.shutdown_event.is_set():
            pass
        self.log.debug("in shutdown() self.shutdown_event = " + str(self.shutdown_event.is_set()) + "shutting down.")


class HttpConnectionListener(Thread):
    def __init__(self, listening_port, queue, shutdown_event):
        super(HttpConnectionListener, self).__init__()
        self.log = logging.getLogger('http_controller_module.HttpConnectionListener')
        self.port = listening_port # port to listen on for new connections
        self.shutdown_event = shutdown_event
        self.queue = queue
        self.connections = {} # maps ports to events
        self.connection_events = {}
        self.log.debug("Creating HttpConnectionListener")

    def run(self):
        host = ''
        self.log.debug("creating socket")
        listener = socket(AF_INET, SOCK_STREAM)
        listener.settimeout(.5)
        listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            self.log.debug("binding to port " + str(self.port))
            listener.bind((host, self.port))
            self.log.debug("listening for connections")
            listener.listen(5)
        except:
            self.log.exception('exception thrown while binding to listening socket at port ' + str(self.port))
            self.shutdown_listeners()

        try:
            self.log.debug("waiting for incoming connections")
            while not self.shutdown_event.is_set():
                self.remove_dead_connections()
                try:
                    (clientsocket, address) = listener.accept()
                    self.log.debug('got connection from ' + str(address))
                    self.connection_events[address] = Event()
                    clientsocket.settimeout(20)
                    HttpListener(address, clientsocket, self.queue, self.connection_events[address]).start()
                except timeout:
                    pass
                except:
                    self.log.exception('exception thrown while accepting new connections')
                    break
        except:
            self.log.exception('exception thrown while listening to new connections')
        finally:
            self.log.info('Shutting down HttpConnectionListener thread')
            self.shutdown_listeners()
            listener.close()

    def shutdown_listeners(self):
        self.log.debug('Shutting down ' + str(len(self.connection_events)) + ' connections')
        for address, event in self.connection_events.iteritems():
            event.set()

        while len(self.connection_events) > 0:
            self.remove_dead_connections(False)

        self.shutdown_event.clear()

    def remove_dead_connections(self, event_state=True):
        dead_ports = []
        for addr, event in self.connection_events.iteritems():
            if event.is_set() == event_state:
                dead_ports.append(addr)
        for addr in dead_ports:
            self.log.debug('removing connection ' + str(addr[1]))
            del self.connection_events[addr]


class HttpListener(Thread):
    def __init__(self, addr, socket, queue, event):
        super(HttpListener, self).__init__()
        self.log = logging.getLogger('http_controller_module.HttpListener')
        self.log.debug("creating listener on addr = " + str(addr))
        self.addr = addr
        self.queue = queue
        self.socket = socket
        self.shutdown_event = event

    def run(self):
        log.debug('connecting an http listener on addr(' + str(self.addr[0]) + ', ' + str(self.addr[1]) + ')')
        shutdown_str = 'http listener on addr(' + str(self.addr[0]) + ', ' + str(self.addr[1]) + ') closing'
        while not self.shutdown_event.is_set():
            try:
                data = self.socket.recv(1024)
                if data:
                    log.debug('data = ' + str(data))
                else:
                    self.close_down_listener(['socket disconnection occurred on addr(' + str(self.addr[0]) + ', ' +
                                              str(self.addr[1]) + ') closing socket',
                                              shutdown_str], True)
                    return
            except timeout:
                self.log.debug('timeout occurred on addr(' + str(self.addr[0]) + ', ' + str(self.addr[1]) + ')')
                if not self.shutdown_event.is_set():
                    self.close_down_listener(['dead http listener on addr(' +
                                              str(self.addr[0]) + ', ' + str(self.addr[1]) + ') closing',
                                              shutdown_str], True)
                    return

        self.close_down_listener(['closing socket for addr(' + str(self.addr[0]) + ', ' + str(self.addr[1]) + ')',
                                  shutdown_str])

    def close_down_listener(self, output_list, set_event=False):
        for output in output_list:
            self.log.info(output)

        if set_event:
            self.shutdown_event.set()
        else:
            self.shutdown_event.clear()
            
        self.socket.close()



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
                # log.debug('done getting value')
            except Empty:
                #log.debug("queue empty on get call") # noisy logging
                pass
            else:
                try:
                    log.debug("hello")
                    #nums.append(int(val))
                    #log.info('value received = ' + str(val))
                # queue.task_done()
                except:
                    pass
    except KeyboardInterrupt:
        log.info('Keyboard interrupt received. Shutting down connection listeners')
        print '\nShutting down remaining open listeners please wait...'
        connection_listener.shutdown()
        log.info('length of array = ' + str(len(nums)))
        log.info(str(sorted(nums)))
        log.info('All present: ' + str(analyze_queue(nums)))
        log.info('Shutting down main')
        print 'Closing program'