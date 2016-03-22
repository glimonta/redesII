# coding=utf-8

import optparse, os

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver
from movie import Movie, MovieList, Server, Client

movies = {}
servers = []

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


class RegisterServerProtocol(NetstringReceiver):

    def stringReceived(self, request):
        if '.' not in request:
            self.bad_request()

        try:
            num_movies_info, movies = request.split(',', 1)
            _, _, num_movies_info = num_movies_info.split(':', 2)
            name, value = num_movies_info.split('.', 1)
            if ('lista_peliculas' == name):
                self.movie_list = []
                self.number_of_movies = int(value)
            for index in range(self.number_of_movies):
                movie_info, movies = movies.split(',', 1)
                _, movie_info = movie_info.split(':', 1)
                name, value = movie_info.split('.', 1)
                if ('id_pelicula' == name):
                    self.movie_list.append((name, value))
            self.add_new_download_server()
        except ValueError:
            self.bad_request()

    def closeConnection(self):
        self.transport.loseConnection()

    def print_movie_list(self):
        for movie in movies:
            print 'id_pelicula:', movie
            print 'servidores:', movies[movie]
            print '---------------------'


    def add_new_download_server(self):
        host = self.transport.getPeer().host
        port = self.transport.getPeer().port
        for movie in self.movie_list:
            if movie[1] not in movies:
                movies[movie[1]] = [(host, port)]
            else:
                movies[movie[1]].append((host, port))
        servers.append(Server(host, port))
        self.print_movie_list()
        self.sendString('2:Ok,')
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()

    def bad_request(self):
        self.sendString('11:Bad request,')
        self.transport.loseConnection()


class RegisterServerFactory(ServerFactory):

    protocol = RegisterServerProtocol

    def __init__(self):
        self.init = True

class RegisterClientProtocol(NetstringReceiver):

    users = []

    def stringReceived(self, request):
        if '.' not in request:
            self.bad_request()

        try:
            _, request = request.split(':', 2)
            name, value = request.split('.', 1)
            if ('registro' == name):
                host = self.transport.getPeer().host
                port = self.transport.getPeer().port
                self.users.append(Client(value, host, port))
                self.sendString('2:Ok,')
                self.transport.loseConnection()
        except ValueError:
            self.bad_request()

    def closeConnection(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()

    def bad_request(self):
        self.sendString('11:Bad request,')
        self.transport.loseConnection()


class RegisterClientFactory(ServerFactory):

    protocol = RegisterClientProtocol

    def __init__(self):
        self.init = True

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

    def movies_by_server(self):
        for server in servers:
            self.sendLine('server:')
            self.sendLine('  ' + server.to_string())
            self.sendLine('movies:')
            for movie in movies:
                if server.to_server() in movies[movie]:
                    self.sendLine('  ' + movie)

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
                self.sendLine(client[0] + ': ' + client[1])


class ConsoleService(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port

    #def connect_server(self):
    #    factory = RegisterServerFactory()
    #    factory.deferred.addCallback(self.print_confirmation)
    #    from twisted.internet import reactor
    #    reactor.connectTCP(self.host, self.port, factory)
    #    return factory.deferred

    #def print_confirmation(self, reply):
    #    return reply

def main():
    options, poetry_file = parse_args()

    factory_server = RegisterServerFactory()
    factory_client = RegisterClientFactory()

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
