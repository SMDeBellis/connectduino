#!/usr/bin/python

from threading import Thread, Event
from Queue import Queue, Empty, Full
from serial import Serial
from serial.tools.list_ports import comports
import logging
from time import sleep
from sys import platform
from os import path, makedirs
######################Logging setup##########################################

log = logging.getLogger('serial_controller_module')
log.setLevel(logging.INFO)

#create a file handler
if 'win' in platform:
    log_dir = 'C:\\ProgramData\\connectduino\logs\\'
else:
    log_dir = '/var/log/connectduino/'

if not path.exists(log_dir):
    makedirs(log_dir)

file_name = 'serialduino.log'

handler = logging.FileHandler(path.join(log_dir, file_name))
handler.setLevel(logging.INFO)

#create a Logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

#add the handlers to the Logger
log.addHandler(handler)


class SerialController:

    def __init__(self, queue):
        self.serial_connections = {}
        self.data_queue = queue
        self.shutdown_event = Event()
        self.serial_connection_listener = SerialConnectionListener(self.shutdown_event, self.data_queue)
        self.serial_connection_listener.start()
        self.log = logging.getLogger('serial_controller_module.SerialController')
        self.log.debug("leaving SerialController init method")


    def shutdown(self):
        self.shutdown_event.set()
        while self.shutdown_event.is_set():
            pass


class SerialConnectionListener(Thread):

    def __init__(self, shutdown_event, data_queue):
        super(SerialConnectionListener, self).__init__()
        self.shutdown_time = shutdown_event
        self.listener_map = {}
        self.listener_shutdown_event_map = {}
        self.data_queue = data_queue
        self.log = logging.getLogger('serial_controller_module.SerialConnectionListener')

    def run(self):
        log.info("running SerialConnectionListener thread")
        try:
            while not self.shutdown_time.is_set():
                #log.debug('checking for ports')
                self.remove_dead_ports()
                #check for new connections
                ports = comports()
                #log.debug('ports found = ' + str(ports))
                for port in ports:
                    if port.device not in self.listener_map:
                        self.listener_shutdown_event_map[port.device] = Event()
                        self.listener_map[port.device] = SerialListener(port.device, self.listener_shutdown_event_map[port.device], self.data_queue)
                        self.listener_map[port.device].start()
                        self.log.info("Listener created on port " + port.device)

                self.log.debug('connected ports = ' + str(self.listener_map.keys()))
                #sleep(.1)

        except:
            self.log.exception("Exception caught in SerialConnectionListener")

        finally:
            self.log.info('Shutting down SerialConnectionListener thread')
            self.shutdown_listeners()


    def remove_dead_ports(self):
        #self.log.debug('removing dead ports')
        dead_ports = []
        for port, event in self.listener_shutdown_event_map.iteritems():
            if event.is_set():
                dead_ports.append(port)
        for port in dead_ports:
            self.log.debug('shutting down dead port' + port)
            del self.listener_shutdown_event_map[port]
            del self.listener_map[port]


    def shutdown_listeners(self):
        for port, event in self.listener_shutdown_event_map.iteritems():
            event.set()

        while len(self.listener_map) > 0:
            dead_listeners = []
            for port, listener in self.listener_map.iteritems():
                if not listener.is_alive():
                    dead_listeners.append(port)
            for port in dead_listeners:
                del self.listener_map[port]
            #log.debug('waiting on ' + str(self.listener_map.keys()))

        self.shutdown_time.clear()


class SerialListener(Thread):

    def __init__(self, port, shutdown_event, data_queue):
        super(SerialListener, self).__init__()
        self.port = port
        self.shutdown_event = shutdown_event
        self.data_queue = data_queue
        self.log = logging.getLogger('serial_controller_module.SerialListener-' + self.port)


    def run(self):
        try:
            #connect to port
            self.log.debug('connecting to serial port ' + self.port)
            conn = Serial(self.port, timeout=.005)
            while not self.shutdown_event.is_set():
                #get data from port
                #self.log.debug('reading data from port ' + self.port)
                self.log.debug('self.shutdown_event.is_set() = ' + str(self.shutdown_event.is_set()))
                data = conn.readline()
                self.log.debug('done reading data from port ' + self.port)
                if data:
                    #self.log.debug('queueing data = ' + data)
                    try:
                        log.debug('queuing data')
                        self.data_queue.put_nowait(data)
                    except Full:
                        log.error('queue is full discarding data = ' + data)
                    else:
                        self.log.debug('data queued = ' + data)
                #else:
                #    self.log.debug('no data read from port ' + self.port)

            self.log.debug('self.shutdown_event.is_set() = ' + str(self.shutdown_event.is_set()))
            self.log.info('shutdown event received closing port ' + self.port)
            conn.close()
            self.shutdown_event.clear()

        except:
            self.log.exception('exception thrown, shutting down port ' + self.port)
            self.shutdown_event.set()


if __name__ == '__main__':

    log.info('\n\n#######################Starting up Server############################')
    # queue = Queue()
    #
    # log.info('creating connection_listener')
    # connection_listener = SerialController(queue)
    #
    # try:
    #     while True:
    #         try:
    #             #log.debug('getting value')
    #             val = queue.get(timeout=.05)
    #             queue.task_done()
    #             #log.debug('done getting value')
    #         except Empty:
    #             log.debug("queue empty on get call") # noisy logging
    #             pass
    #         else:
    #             log.info('value received = ' + str(val))
    #             #queue.task_done()
    #
    # except KeyboardInterrupt:
    #     log.info('Keyboard interrupt received. Shutting down connection listener')
    #     connection_listener.shutdown()
    #     log.info('Shutting down main')

