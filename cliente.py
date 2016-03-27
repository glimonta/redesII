# coding=utf-8
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
An example of reading a line at a time from standard input
without blocking the reactor.
"""

import optparse

from twisted.internet             import stdio
from twisted.protocols            import basic
from twisted.protocols.basic      import NetstringReceiver
from twisted.internet.protocol    import Protocol, ClientFactory
from twisted.internet.defer       import Deferred, maybeDeferred
from movie                        import Movie, MovieList
from twisted.words.xish.domish    import Element, IElement
from twisted.words.xish.xmlstream import XmlStream, XmlStreamFactory


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

class RegisterServerProtocol(XmlStream):

    reply = ''
    movies = MovieList()

    def __init__(self):
        XmlStream.__init__(self)    # possibly unnecessary
        self._initializeStream()

    def sendObject(self, obj):
        if IElement.providedBy(obj):
            print "[TX]: %s" % obj.toXml()
        else:
            print "[TX]: %s" % obj
        self.send(obj)

    def connectionMade(self):
        request = Element((None, 'register_client'))
        request['host'] = self.transport.getHost().host
        request['port'] = str(self.transport.getHost().port)
        request.addElement('username').addContent(self.factory.username)
        self.sendObject(request)

    def dataReceived(self, data):
        """ Overload this function to simply pass the incoming data into the XML parser """
        try:
            self.stream.parse(data)
        except Exception as e:
            self._initializeStream()

    def onDocumentStart(self, elementRoot):
        """ The root tag has been parsed """
        print('Root tag: {0}'.format(elementRoot.name))
        print('Attributes: {0}'.format(elementRoot.attributes))
        if elementRoot.name == 'registration_reply':
            self.action = 'registration_reply'
            if (elementRoot.attributes['reply'] == 'Ok'):
                print 'Se registró exitosamente en el servidor central'
            else:
                print 'No se registró en el servidor central'

    def onElement(self, element):
        """ Children/Body elements parsed """
        print('\nElement tag: {0}'.format(element.name))
        print('Element attributes: {0}'.format(element.attributes))
        print('Element content: {0}'.format(element))

    def onDocumentEnd(self):
        """ Parsing has finished, you should send your response now """

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
