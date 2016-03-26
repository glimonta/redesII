# coding=utf-8
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
An example of reading a line at a time from standard input
without blocking the reactor.
"""

import optparse

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.protocols.basic import NetstringReceiver
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.defer import Deferred, maybeDeferred
from movie import Movie, MovieList


def parse_args():
    usage = """%prog [options] [ip_servidor]:puerto_servidor ...

Éste es el servidor de descarga.
Se corre de la siguiente manera:

python servidor-descarga.py ip_servidor:puerto_servidor

donde la ip y el puerto pertenecen al servidor central de la aplicación.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one server address.')

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return options, parse_address(args[0])

class ConsoleProtocol(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, service):
        self.service = service
        #d = self.service.connect_server()

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if ('INSCRIPCION' in line):
            _, username = line.split(' ', 1)
            self.sendLine('Quiero inscribirme con el nombre ' + username)
            d = self.service.connect_server(username)
            self.transport.write('>>> ')
        elif ('PELICULAS' == line):
            self.sendLine('Quiero saber cuales son las peliculas del servidor')
            self.service.list_movies()
            self.transport.write('>>> ')
        elif ('PELICULA' in line):
            _, movie = line.split(' ', 1)
            self.sendLine('Quiero descargar la pelicula ' + movie)
            self.transport.write('>>> ')
        elif ('STATUS' in line):
            _, movie = line.split(' ', 1)
            self.sendLine('Quiero saber el status de la pelicula ' + movie)
            self.transport.write('>>> ')
        elif ('SALIR' == line):
            self.console_finished_running();
        else:
            self.sendLine('Echo: ' + line)
            self.transport.write('>>> ')

    def console_finished_running(self):
        from twisted.internet import reactor
        print 'Hasta luego'
        self.transport.loseConnection()
        reactor.stop()

class RegisterServerProtocol(NetstringReceiver):

    reply = ''
    movies = MovieList()

    def connectionMade(self):
        #string = 'registro.' + self.factory.username
        #length = str(len(string))
        #self.sendString(length + ':' + string + ',')
        self.sendString('register.' + self.factory.username)

    def stringReceived(self, request):
        if 'Ok' in request:
            self.reply = 'Ok'
            self.confirmationReceived(self.reply)
        elif 'Bad request' in request:
            self.reply = 'Bad connection'
            self.connectionLost(self.reply)
        else:
            self.reply = None
            self.confirmationReceived()

    def connectionLost(self, reason):
        self.confirmationReceived(self.reply)

    def confirmationReceived(self, reply):
        self.factory.reply_received(reply)

class RegisterServerFactory(ClientFactory):

    protocol = RegisterServerProtocol

    def __init__(self, username):
        self.deferred = Deferred()
        self.username = username

    def reply_received(self, reply):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(reply)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason, connector.getDestination())

class ListMovieServerProtocol(NetstringReceiver):

    reply = ''
    movies = MovieList()

    def connectionMade(self):
        self.sendString('list_movies.0')

    def stringReceived(self, request):
        if '.' not in request:
            self.transport.loseConnection()
            return

        action, parameter = request.split('.', 1)

        peer = self.transport.getPeer()
        self.request_received(action, parameter, peer)

    def request_received(self, action, parameter, peer):
        thunk = getattr(self, 'do_%s' % (action,), None)

        if thunk is None:
            return None

        try:
            return thunk(parameter, peer)
        except:
            return None

    def do_id_movie(self, id_movie, peer):
        self.id_movie = id_movie

    def do_movie_title(self, title, peer):
        movie = Movie(self.id_movie, title)
        if movie not in self.factory.movies:
            self.factory.movies.append(movie)

    def do_end_list(self, value, peer):
        self.factory.list_received(self.factory.movies)

    def connectionLost(self, reason):
        self.confirmationReceived(self.reply)

    def confirmationReceived(self, movie_list):
        self.factory.list_received(movie_list)

class ListMovieServerFactory(ClientFactory):

    protocol = ListMovieServerProtocol
    movies = []

    def __init__(self):
        self.deferred = Deferred()

    def list_received(self, movie_list):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(movie_list)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason, connector.getDestination())

class ConsoleService(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def connect_server(self, username):
        factory = RegisterServerFactory(username)
        factory.deferred.addCallback(self.print_confirmation)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred

    def list_movies(self):
        factory = ListMovieServerFactory()
        factory.deferred.addCallback(self.print_movie_list)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred

    def print_confirmation(self, reply):
        return reply

    def print_movie_list(self, movies):
        print ''
        print '----------------------------------------'
        for movie in movies:
            print movie.to_string()
            print '----------------------------------------'

def main():

    options, server_addr = parse_args()

    from twisted.internet import reactor

    service = ConsoleService(*server_addr)
    stdio.StandardIO(ConsoleProtocol(service), 0, 1, reactor)
    reactor.run()

if __name__ == '__main__':
    main()
