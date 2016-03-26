# coding=utf-8

import optparse, os

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver
from movie import Movie, MovieList, Server, Client

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


class DownloadServerProtocol(NetstringReceiver):

    id_movie = None

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

    def do_server_host(self, host, peer):
        self.factory.server_host = host
        return 'Ok'

    def do_server_port(self, port, peer):
        self.factory.server_port = port
        self.factory.ser = Server(self.factory.server_host, self.factory.server_port)
        return 'Ok'

    def do_number_of_movies(self, number, peer):
        number_of_movies = number
        return 'Ok'

    def do_id_movie(self, id_movie, peer):
        self.id_movie = id_movie
        return 'Ok'

    def do_movie_title(self, title, peer):
        movie = Movie(self.id_movie, title)
        if movie not in movies:
            movies[movie] = [self.factory.ser]
        else:
            movies[movie].append(self.factory.ser)
        return 'Ok'

    def do_last_movie_title(self, title, peer):
        movie = Movie(self.id_movie, title)
        if movie not in movies:
            movies[movie] = [self.factory.ser]
        else:
            movies[movie].append(self.factory.ser)
        self.add_new_download_server()
        return 'Ok'

    def closeConnection(self):
        self.transport.loseConnection()

    def print_movie_list(self):
        for movie in movies:
            print movie.to_string()
            print 'server:'
            for server in movies[movie]:
                print server.to_string()
            print '---------------------'


    def add_new_download_server(self):
        servers.append(self.factory.ser)
        #self.print_movie_list()
        self.sendString('Ok')
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()

    def bad_request(self):
        self.sendString('11:Bad request,')
        self.transport.loseConnection()


class DownloadServerFactory(ServerFactory):

    protocol = DownloadServerProtocol
    movie_list = []

    def __init__(self):
        self.init = True


class ClientProtocol(NetstringReceiver):

    users = []

    def stringReceived(self, request):
        if '.' not in request:
            self.transport.loseConnection()
            return

        action, parameter = request.split('.', 1)

        peer = self.transport.getPeer()
        self.request_received(action, parameter, peer)

    def request_received(self, action, parameter, peer):
        result = self.factory.do_action(action, parameter, peer)

        if result is not None:
            self.sendString('Ok')
        else:
            self.sendString('Bad request')
        self.transport.loseConnection

    def closeConnection(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()

    def bad_request(self):
        self.sendString('11:Bad request,')
        self.transport.loseConnection()


class ClientFactory(ServerFactory):

    protocol = ClientProtocol

    def __init__(self, service):
        self.init = True
        self.service = service

    def do_action(self, action, parameter, peer):
        thunk = getattr(self, 'do_%s' % (action,), None)

        if thunk is None:
            return None

        try:
            return thunk(parameter, peer)
        except:
            return None

    def do_register(self, username, peer):
        return self.service.register_user(username, peer)

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
                self.sendLine(client[0] + ': ' + client[1])


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
