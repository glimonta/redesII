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
from twisted.internet.protocol    import Protocol, ClientFactory, ServerFactory
from twisted.internet.defer       import Deferred, maybeDeferred
from movie                        import Movie, MovieList
from twisted.words.xish.domish    import Element, IElement
from twisted.words.xish.xmlstream import XmlStream, XmlStreamFactory

movies = []

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

    if len(args) != 2:
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

    return options, parse_address(args[0]), parse_address(args[1])

class ConsoleProtocol(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, service):
        self.service = service
        d = self.service.connect_server()

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if ('PELICULAS_DESCARGANDO' == line):
            self.sendLine('Quiero ver cuantas peliculas se están descargando')
            self.transport.write('>>> ')
        elif ('PELICULAS_DESCARGADAS' == line):
            self.sendLine('Quiero saber cuantas peliculas se han descargado')
            self.transport.write('>>> ')
        elif ('CLIENTES_FIELES' == line):
            self.sendLine('¿Quiénes son los clientes fieles?')
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

    def __init__(self):
        XmlStream.__init__(self)    # possibly unnecessary
        self._initializeStream()
        m = Movie('potter', 'Harry Potter', 123)
        m1 = Movie('anillos', 'Lord of the Rings', 512)
        m2 = Movie('wars', 'Star Wars', 463)
        movie_list = [m,m1,m2]
        for movie in movie_list:
            movies.append(movie)

    def sendObject(self, obj):
        if IElement.providedBy(obj):
            print "[TX]: %s" % obj.toXml()
        else:
            print "[TX]: %s" % obj
        self.send(obj)

    def connectionMade(self):
        request = Element((None, 'register_download_server'))
        request['host'] = self.factory.host
        request['port'] = str(self.factory.port)
        for movie in movies:
            m = request.addElement('movie')
            m['id_movie'] = movie.id_movie
            m['title'] = movie.title
            m['size'] = str(movie.size)
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

    def __init__(self, host, port):
        self.deferred = Deferred()
        self.host = host
        self.port = port

    def reply_received(self, reply):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(reply)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

class ClientProtocol(XmlStream):

    def __init__(self):
        XmlStream.__init__(self)    # possibly unnecessary
        self._initializeStream()
        print 'oook'

    def sendObject(self, obj):
        if IElement.providedBy(obj):
            print "[TX]: %s" % obj.toXml()
        else:
            print "[TX]: %s" % obj
        self.send(obj)

    def list_movies(self):
        request = Element((None, 'movie_list'))
        for movie in movies:
            m = request.addElement('movie')
            m['id_movie'] = movie.id_movie
            m['title'] = movie.title
            m['size'] = str(movie.size)
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
        if elementRoot.name == 'request_movie':
            self.action = 'request_movie'

    def onElement(self, element):
        """ Children/Body elements parsed """
        print('\nElement tag: {0}'.format(element.name))
        print('Element attributes: {0}'.format(element.attributes))
        print('Element content: {0}'.format(element))
        if element.name == 'id_movie':
            self.id_movie = str(element)
        else:
            print element.name

    def onDocumentEnd(self):
        print self.action
        """ Parsing has finished, you should send your response now """
        if self.action == 'request_movie':
            self.send_movie(self.id_movie)

    def send_movie(self, movie):
        for m in movies:
            if m.id_movie == movie:
                request = Element((None, 'movie_download'))
                self.sendObject(request)

    def closeConnection(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()


class ClientRequestsFactory(ServerFactory):

    protocol = ClientProtocol

    def __init__(self):
        self.init = True

class ConsoleService(object):

    def __init__(self, server_host, server_port, host, port):
        self.server_host = server_host
        self.server_port = server_port
        self.host = host
        self.port = port

    def connect_server(self):
        factory = RegisterServerFactory(self.host, self.port)
        factory.deferred.addCallback(self.print_confirmation)
        from twisted.internet import reactor
        reactor.connectTCP(self.server_host, self.server_port, factory)
        return factory.deferred

    def print_confirmation(self, reply):
        return reply

def main():

    options, server_addr, addr = parse_args()

    server_host, server_port = server_addr
    host, port = addr

    from twisted.internet import reactor


    factory_client = ClientRequestsFactory()
    port_for_client = reactor.listenTCP(port or 0, factory_client, interface=options.iface)

    service = ConsoleService(server_host, server_port, host, port)
    stdio.StandardIO(ConsoleProtocol(service), 0, 1, reactor)
    reactor.run()

if __name__ == '__main__':
    main()
