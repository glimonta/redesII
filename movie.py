class Movie:

    def __init__(self, id_movie, title):
        self.id_movie = id_movie
        self.title = title

    def to_netstring(self):
        string = 'id_pelicula.' + self.id_movie
        length = len(string)
        return str(length) + ':' + string + ','

class MovieList:

    def __init__(self):
        self.movies = []

    def add_movie(self, movie):
        self.movies.append(movie)

    def to_netstring(self):
        movie_list_len = len(self.movies)
        string = 'lista_peliculas.' + str(movie_list_len)
        length = len(string)
        string = str(length) + ':' + string + ','
        for index in range(movie_list_len):
            string += self.movies[index].to_netstring()
        total_length = len(string)
        print str(total_length) + ':' + string + ','
        return str(total_length) + ':' + string + ','

class Client:

    def __init__(self, name, host, port):
        self.name = name
        self.host = host
        self.port = port

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
        return (self.host, self.port)

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

