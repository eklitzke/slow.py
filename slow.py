import optparse
import os
import socket
import sys
import time

import tornado.ioloop
import tornado.iostream

class HTTPClient(object):

    USER_AGENT = 'slow.py'

    def __init__(self, host, path, delay, finish_cb=None, io_loop=None):
        self.host = host
        self.path = path
        self.delay = delay / 1000.0
        if io_loop is None:
            io_loop = tornado.ioloop.IOLoop.instance()
        self.io_loop = io_loop
        self.finish_cb = finish_cb

        self.request = 'GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: %s\r\n\r\n' % (self.path, self.host, self.USER_AGENT)
        self.pos = 0

    def send_byte(self):
        self.stream.write(self.request[self.pos])
        self.pos += 1
        if self.pos < len(self.request):
            self.io_loop.add_timeout(time.time() + self.delay, self.send_byte)
        else:
            # don't bother to read the response -- just disconnect
            self.stream.close()
            if callable(self.finish_cb):
                self.finish_cb()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(tornado.iostream.IOStream, 'connect'):
            # this behavior is supported only by newer tornados
            self.stream = tornado.iostream.IOStream(sock)
            self.stream.connect((self.host, 80), self.send_byte)
        else:
            # n.b. this is a blocking connect
            sock.connect((self.host, 80))
            self.stream = tornado.iostream.IOStream(sock)
            self.send_byte()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-c', '--count', default=20, type='int', help='How many connections to open')
    parser.add_option('--host', help='The host to connect to')
    parser.add_option('-p', '--path', default='/', help='The path to fetch')
    parser.add_option('-d', '--delay', default=500, type='int', help='The delay to use, in milliseconds')
    parser.add_option('-v', '--verbose', default=False, action='store_true', help='Print dots to the screen as clients finish')
    opts, args = parser.parse_args()
    if not opts.host:
        parser.error('Must specify a host to connect to')

    io_loop = tornado.ioloop.IOLoop.instance()

    finished = [0]
    def finish_cb():
        """Called after each client is finished"""
        if opts.verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
        finished[0] += 1
        if finished[0] >= opts.count:
            if opts.verbose:
                sys.stdout.write(os.linesep)
            io_loop.stop()

    clients = [HTTPClient(opts.host, opts.path, opts.delay, finish_cb=finish_cb, io_loop=io_loop)
               for x in xrange(opts.count)]
    for client in clients:
        client.run()
    io_loop.start()
