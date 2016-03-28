# coding=utf-8
class Movie:

    def __init__(self, id_movie, title, size):
        self.id_movie = id_movie
        self.title = title
        self.size = size

    def get_id(self):
        return self.id_movie

    def get_title(self):
        return self.title

    def get_size(self):
        return self.size

    def to_string(self):
        return "id_pelicula: " + self.id_movie + ", titulo: " + self.title + ", size: " + str(self.size)


class MovieList:
    """ Tiene un diccionario de peliculas que tiene key=movie, value=serverList"""
    def __init__(self):
        self.movies = {}

    def is_element(self, movie):
        for m in self.movies:
            if m == movie: return True
        return False

    def add_movie(self, movie, server):
        if movie not in self.movies:
            self.movies[movie] = [server]
        else:
            self.movies[movie].append(server)

    def get_movie_dict(self):
        return self.movies

    def get_movie(self, id_movie):
        for movie in self.movies:
            if movie.get_id() == id_movie:
                return movie
        return None

    def get_servers(self, movie):
        return self.movies[movie]

    def print_movies(self):
        for movie in self.movies:
            print movie.to_string()
            print 'server:'
            for server in self.movies[movie]:
                print server.to_string()
            print '---------------------'

    def get_download_server_list(self, movie):
        #Idealmente luego queremos devolver solo un servidor, el ideal
        return self.movies[movie]

class Client:

    def __init__(self, username, host, port):
        self.username = username
        self.host = host
        self.port = port

    def to_string(self):
        return self.username + ' ' + self.host + ' ' + str(self.port)

class Server:

    def __init__(self, host, port, clients=[], active_downloads=[], finished_downloads=[], downloaded_movies=[]):
        self.host = host
        self.port = port
        self.clients = clients
        self.active_downloads = active_downloads
        self.finished_downloads = finished_downloads
        self.downloaded_movies = downloaded_movies

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def to_string(self):
        return '(\'' + self.host + '\', ' + str(self.port) + ')'

    def to_server(self):
        return (str(self.host), self.port)

    def add_download(self, client, movie):
        self.active_downloads.append((client, movie))
        exists = False
        for c in self.clients:
            if client == c[0]:
                c[1] += 1
                exists = True
        if not exists:
            self.clients.append((client, 1))

    def finished_download(self, client, movie):
        if (client, movie) in self.active_downloads:
            self.active_downloads.remove((client, movie))
            self.finished_downloads.append((client, movie))
        exists = false
        for m in self.downloaded_movies:
            if movie in m[0]:
                m[1] += 1
                exists = true
        if not exists:
            self.downloaded_movies.append((movie, 1))

class ServerList:
    """ Tiene un diccionario de peliculas que tiene key=movie, value=serverList"""
    def __init__(self):
        self.servers = []

    def is_element(self, server):
        for s in self.servers:
            if s == server: return True
        return False

    def add_server(self, server):
        self.servers.append(server)

    def get_server_list(self):
        return self.servers

    def get_server(self, host, port):
        for server in self.servers:
            if server.get_host() == host and server.get_port() == port:
                return server
        return None

    def get_server(self, server):
        for s in self.servers:
            if s == server:
                return s
        return None

    def print_servers(self):
        for server in self.servers:
            print server.to_string()

class Request:

    def __init__(self, movie, server):
        self.movie = movie
        self.server = server

    def to_string(self):
        return 'request: movie:' + self.movie.to_string() + ', server:' + self.server.to_string()
