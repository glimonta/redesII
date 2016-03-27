# coding=utf-8
class Movie:

    def __init__(self, id_movie, title, size):
        self.id_movie = id_movie
        self.title = title
        self.size = size

    def to_string(self):
        return "id_pelicula: " + self.id_movie + ", titulo: " + self.title + ", size: " + str(self.size)


class MovieList:

    def __init__(self):
        self.movies = []

    def __len__(self):
        return len(self.movies)

    def add_movie(self, movie):
        self.movies.append(movie)

class Client:

    def __init__(self, name, host, port):
        self.name = name
        self.host = host
        self.port = port

    def to_string(self):
        return self.name + ' ' + self.host + ' ' + str(self.port)

class Server:

    def __init__(self, host, port, clients=[], active_downloads=[], finished_downloads=[], downloaded_movies=[]):
        self.host = host
        self.port = port
        self.clients = clients
        self.active_downloads = active_downloads
        self.finished_downloads = finished_downloads
        self.downloaded_movies = downloaded_movies

    def to_string(self):
        return '(\'' + self.host + '\', ' + str(self.port) + ')'

    def to_server(self):
        return (str(self.host), self.port)

    def add_client(self):
        self.clients += 1

    def add_download(self, client, movie):
        self.active_downloads.append((client, movie))
        exists = false
        for c in self.clients:
            if client in c[0]:
                c[1] += 1
                exists = true
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
