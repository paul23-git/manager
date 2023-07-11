import re


class ServerData:
    # Utility class to handle server data in docker services
    def __init__(self, path: str, name: str, port: int):
        self.path = path
        self.name = name
        self.port = port

    def __str__(self):
        return '{path}:{name}:{port}'.format(path=self.path, name=self.name, port=self.port)

    def is_more_generic(self, other_data: 'ServerData'):
        return re.match(self.path, other_data.path) is not None
