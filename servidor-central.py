# coding=utf-8

import optparse, os

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver

movies = {}

def print_movie_list():
    for movie in movies:
        print 'id_pelicula:', movie
        print 'servidores:', movies[movie]
        print '---------------------'

def parse_args():
    usage = """ %prog [options]

Éste es el servidor central.
Se corre de la siguiente manera:

  python servidor-central.py

"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

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
            self.transport.write('Bad request')
            self.transport.loseConnection()
            return

        _, string = request.split(':', 1)
        string, _ = string.split(',', 1)
        name, value = string.split('.', 1)
        if ('lista_peliculas' == name):
            self.movie_list = []
            self.number_of_movies = int(value)
        elif ('id_pelicula' == name):
            self.movie_list.append((name, value))
            self.number_of_movies -= 1
            if self.number_of_movies == 0:
                self.add_new_download_server()

    def add_new_download_server(self):
        global movies
        host = self.transport.getPeer().host
        port = self.transport.getPeer().port
        for movie in self.movie_list:
            if movie[1] not in movies:
                movies[movie[1]] = [(host, port)]
            else:
                movies[movie[1]].append((host, port))
        print_movie_list()
        self.transport.write('Ok')
        self.transport.loseConnection()

    def connectionMade(self):
        print 'Nueva conexión desde', self.transport.getPeer()


class RegisterServerFactory(ServerFactory):

    protocol = RegisterServerProtocol

    def __init__(self):
        self.init = True


def main():
    options, poetry_file = parse_args()

    factory = RegisterServerFactory()

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Esperando por conexiones en %s' % (port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()
