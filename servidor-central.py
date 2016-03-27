# coding=utf-8

import optparse, os

from twisted.internet             import stdio
from twisted.protocols            import basic
from twisted.internet.protocol    import ServerFactory, Protocol
from twisted.protocols.basic      import NetstringReceiver
from movie                        import Movie, MovieList, Server, Client, Request
from twisted.words.xish.domish    import Element, IElement
from twisted.words.xish.xmlstream import XmlStream, XmlStreamFactory

movies = {}
servers = []
users = {}

def parse_args():
    usage = """ %prog [options]

Éste es el servidor central.
Se corre de la siguiente manera:

  python servidor-central.py

"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port-server', type='int', help=help, dest="port_server")

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port-client', type='int', help=help, dest="port_client")

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    #if len(args) != 1:
        #parser.error('Provide exactly one poetry file.')

    #poetry_file = args[0]
    poetry_file = None

    #if not os.path.exists(args[0]):
    #   parser.error('No such file: %s' % poetry_file)

    return options, poetry_file


class DownloadServerProtocol(XmlStream):

    id_movie = None
    movie_list = []
    host = None
    port = None

    def __init__(self):
        XmlStream.__init__(self)    # possibly unnecessary
        self._initializeStream()

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
        if elementRoot.name == 'register_download_server':
            self.action = 'register_download_server'
            self.host = str(elementRoot.attributes['host'])
            self.port = int(elementRoot.attributes['port'])

    def onElement(self, element):
        """ Children/Body elements parsed """
        print('\nElement tag: {0}'.format(element.name))
        print('Element attributes: {0}'.format(element.attributes))
        print('Element content: {0}'.format(element))
        if element.name == 'movie':
            id_movie = str(element.attributes['id_movie'])
            title = str(element.attributes['title'])
            size = int(element.attributes['size'])
            m = Movie(id_movie, title, size)
            self.movie_list.append(Movie(id_movie, title, size))
        else:
            print element.name

    def onDocumentEnd(self):
        """ Parsing has finished, you should send your response now """
        if self.action == 'register_download_server':
            self.server = Server(self.host, self.port)
            self.add_movie_list()
            servers.append(self.server)
            print 'Se agregó el nuevo servidor: ', self.server.to_string()
            self.registration_ok()

    def sendObject(self, obj):
        if IElement.providedBy(obj):
            print "[TX]: %s" % obj.toXml()
        else:
            print "[TX]: %s" % obj
        self.send(obj)

    def registration_ok(self):
        response = Element((None, 'registration_reply'))
        response['reply'] = 'Ok'
        self.sendObject(response)

    def add_movie_list(self):
        for movie in self.movie_list:
            if movie not in movies:
                movies[movie] = [self.server]
            else:
                movies[movie].append(self.server)


    def closeConnection(self):
        self.transport.loseConnection()

    def print_movie_list(self):
        for movie in movies:
            print movie.to_string()
            print 'server:'
            for server in movies[movie]:
                print server.to_string()
            print '---------------------'


    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()

class DownloadServerFactory(ServerFactory):

    protocol = DownloadServerProtocol
    movie_list = []

    def __init__(self):
        self.init = True


class ClientProtocol(XmlStream):

    def __init__(self):
        XmlStream.__init__(self)    # possibly unnecessary
        self._initializeStream()

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
        if elementRoot.name == 'register_client':
            self.action = 'register_client'
            self.host = str(elementRoot.attributes['host'])
            self.port = int(elementRoot.attributes['port'])
        elif elementRoot.name == 'list_movies':
            self.action = 'list_movies'
        elif elementRoot.name == 'request_movie':
            self.action = 'request_movie'

    def onElement(self, element):
        """ Children/Body elements parsed """
        print('\nElement tag: {0}'.format(element.name))
        print('Element attributes: {0}'.format(element.attributes))
        print('Element content: {0}'.format(element))
        if element.name == 'username':
            self.username = str(element)
        elif element.name == 'id_movie':
            self.id_movie = str(element)
        else:
            print element.name

    def onDocumentEnd(self):
        print self.action
        """ Parsing has finished, you should send your response now """
        if self.action == 'register_client':
            self.client = Client(self.username, self.host, self.port)
            users[self.client] = []
            print 'Se agregó el nuevo cliente: ', self.client.to_string()
            self.registration_ok()
        elif self.action == 'list_movies':
            self.list_movies()
        elif self.action == 'request_movie':
            self.choose_download_server(self.id_movie)

    def choose_download_server(self, movie):
        for m in movies:
            if m.id_movie == movie:
                download_server = movies[m][0]
                mov = m
        request = Element((None, 'download_from'))
        s = request.addElement('server')
        s['host'] = download_server.host
        s['port'] = str(download_server.port)
        for u in users:
            if u.username == self.username:
                client = u
                users[u].append(Request(mov, download_server))
        for s in servers:
            if s == download_server:
                print s.to_string()
                print client.to_string()
                print mov.to_string()
                s.add_download(client, mov)
        self.sendObject(request)


    def closeConnection(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()


class ClientFactory(ServerFactory):

    protocol = ClientProtocol

    def __init__(self, service):
        self.init = True
        self.service = service

class ClientService(object):

    def register_user(self, username, peer):
        c = Client(username, peer.host, peer.port)
        users[c] = []
        print 'El usuario', username, 'ha sido registrado exitosamente.'
        return 'Ok'

class ConsoleProtocol(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, service):
        self.service = service
        #d = self.service.connect_server()

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if ('PELICULASxSERVIDOR' == line):
            self.sendLine('Estas son las películas que hay por servidor:')
            self.movies_by_server()
            self.transport.write('>>> ')
        elif ('DESCARGASxSERVIDOR' == line):
            self.sendLine('Quiero saber cuantas peliculas se han descargado por servidor')
            self.requests_by_server()
            self.transport.write('>>> ')
        elif ('CLIENTESxSERVIDOR' == line):
            self.sendLine('¿Quiénes son los clientes por servidor?')
            self.clients_by_server()
            self.transport.write('>>> ')
        elif('clientes' == line):
            self.sendLine('Los usuarios registrados son:')
            self.registered_users()
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

    def registered_users(self):
        for user in users:
            self.sendLine(user.to_string())

    def movies_by_server(self):
        for server in servers:
            self.sendLine('server:')
            self.sendLine('  ' + server.to_string())
            self.sendLine('movies:')
            for movie in movies:
                if server in movies[movie]:
                    self.sendLine('  ' + movie.to_string())

    def requests_by_server(self):
        for server in servers:
            self.sendLine('server:')
            self.sendLine('  '+ server.to_string())
            self.sendLine('movies:')
            for movie in server.downloaded_movies:
                self.sendLine(movie)

    def clients_by_server(self):
        for server in servers:
            self.sendLine('server:')
            self.sendLine('  ' + server.to_string())
            self.sendLine('clients:')
            for client in server.clients:
                self.sendLine('  ' + client[0].to_string() + ': ' + str(client[1]))


class ConsoleService(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port

def main():
    options, poetry_file = parse_args()

    client_service = ClientService()

    factory_server = DownloadServerFactory()
    factory_client = ClientFactory(client_service)

    from twisted.internet import reactor

    port_server = reactor.listenTCP(options.port_server or 0, factory_server,
                             interface=options.iface)

    port_client = reactor.listenTCP(options.port_client or 0, factory_client,
                             interface=options.iface)

    service = ConsoleService('127.0.0.1', 10000)
    stdio.StandardIO(ConsoleProtocol(service), 0, 1, reactor)

    print 'Esperando por conexiones en %s' % (port_server.getHost())
    print 'Esperando por conexiones en %s' % (port_client.getHost())

    reactor.run()


if __name__ == '__main__':
    main()
