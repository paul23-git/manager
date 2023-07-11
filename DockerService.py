import typing

from ServerData import ServerData
from exportable_compose_part import ExportableComposePart
# from pathlib import Path

# PathLike = typing.Union[str, bytes, Path]


class DockerPort(ExportableComposePart):
    # helper class to specify docker port settings in docker compose file
    def __init__(self, data: typing.Union[str, typing.Dict[str, typing.Union[str, int, None]]]):
        if isinstance(data, str):
            l = data.split('/')
            self.mode = 'host'
            if len(l) > 1:
                self.protocol = l[-1]
                data = ''.join(l[:-1])
            else:
                self.protocol = None
            l = data.split(':')
            self.target = l[-1]
            self.published = ':'.join(l[:-1])
        else:
            self.mode = data.get('mode')
            self.protocol = data.get('protocol')
            self.target = data.get('target')
            self.published = data.get('published')

    def export_data_dict(self) -> typing.Union[str, typing.Dict[str, typing.Union[str, int, None]]]:
        if self.mode == 'host':
            r = '{published}:{target}'.format(published=self.published, target=self.target)
            if self.protocol is not None:
                r += '/{protocol}'.format(protocol=self.protocol)
            return r
        else:
            return {
                'mode': self.mode,
                'protocol': self.protocol,
                'target': self.target,
                'published': self.published,
            }


class DockerService(ExportableComposePart):
    # Generic class to specify docker settings in docker compose file
    def _build_ports(self):
        p = self._dataDict.get('ports')
        self.ports = [DockerPort(port) for port in p] \
            if p is not None else []  # type: typing.List[DockerPort]

    def _build_environment(self):
        if 'environment' not in self._dataDict:
            return None
        env = self._dataDict['environment']
        if isinstance(env, dict):
            self.environment = dict(env)
        elif isinstance(env, list):
            self.environment = dict(elem.split('=', 1) for elem in env)

    def __init__(self, data_dict: dict = None, *args, **kwargs):
        self._dataDict = data_dict if data_dict else {}
        self.ports = None
        self._build_ports()
        self.environment = None
        self._build_environment()

    def get_environment_variable(self, var: str) -> typing.Optional[str]:
        if not self.environment:
            return None
        return self.environment.get(var)

    def set_environment_variable(self, var: str, value: str) -> None:
        if not self.environment:
            self.environment = {}
        self.environment[var] = value

    def get_source_path(self) -> typing.Optional[str]:
        try:
            return self._dataDict['build']['context']
        except KeyError:
            return None

    def export_data_dict(self) -> typing.Optional[dict]:
        d = dict(self._dataDict)
        if self.ports is not None and len(self.ports):
            d['ports'] = [p.export_data_dict() for p in self.ports]

        if self.environment is not None and len(self.environment):
            d['environment'] = dict(self.environment)
        return d

    def get_port(self, i: int) -> DockerPort:
        return self.ports[i]

    def add_port(self, p: DockerPort) -> None:
        self.ports.append(p)

    def remove_port(self, i: typing.Union[int, slice]):
        del self.ports[i]

    def clear_ports(self):
        self.ports = []

    def __str__(self) -> str:
        return str(self._dataDict)

    def __repr__(self) -> str:
        return repr(self._dataDict)

    def get_fullname(self) -> str:
        return self._dataDict['container_name']

    def merge_data(self, data):
        self._dataDict = {**self._dataDict, **data}
        self._build_ports()
        self._build_environment()

    @classmethod
    def generate_empty(cls, base: str, name: str, yaml: dict = None, listenport: int = None, internalport: int = None):
        data_dict = {
            'build': {
                'context': './{base}.{name}/'.format(base=base, name=name)
            },
            'container_name': '{base}.{name}'.format(base=base, name=name),
            'deploy': {
                'restart_policy': {
                    'condition': 'any',
                    'window': '60s',
                }
            },
            'restart': 'unless-stopped',
            'image': '{base}.{name}'.format(base=base, name=name),
            'networks': ['{base}'.format(base=base)],
        }
        if yaml is not None:
            data_dict = {**data_dict, **yaml}
        if listenport is not None and internalport is not None:
            data_dict['ports'] = ['{listenport}:{internalport}'.format(listenport=listenport, internalport=internalport)]
        return cls(data_dict)


class MainDocker(DockerService):
    # Specific docker for the main (nginx/reverse proxy) docker
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        servers = self._getServerEnvironmentVariable()
        self._serverList = list(MainDocker._extract_dynamic_servers(servers))

    def _getServerEnvironmentVariable(self) -> str:
        s = self.get_environment_variable('DYNAMIC_SERVER')
        return s if s is not None else ''

    def merge_data(self, data):
        super().merge_data(data)
        self.set_environment_variable('DYNAMIC_SERVER', self._str_servlist())

    @staticmethod
    def _extract_dynamic_servers(servers: str) -> typing.Generator[ServerData, typing.Any, None]:
        serverList = servers.split(';')
        return (ServerData(*server.split(':')) for server in serverList if server)

    def _str_servlist(self):
        return ";".join(str(server) for server in self._serverList)

    def add_server(self, path: str, server_name: str, server_port: int) -> None:
        new_data = ServerData(path, server_name, server_port)
        try:
            ind, v = next((ind, v) for ind, v in enumerate(self._serverList) if v.is_more_generic(new_data))
            if v.path == new_data.path:
                raise ValueError('{path} already inside path'.format(path=new_data.path))
            self._serverList.insert(ind, new_data)
            self.set_environment_variable('DYNAMIC_SERVER', self._str_servlist())
        except StopIteration:
            self._serverList.append(new_data)

    def remove_server(self, server_name: str) -> None:
        print(len(self._serverList))
        for ind, v in enumerate(self._serverList):
            if v.name == server_name:
                del self._serverList[ind]
        self.set_environment_variable('DYNAMIC_SERVER', self._str_servlist())
        print(len(self._serverList))

    def export_data_dict(self) -> typing.Optional[dict]:
        dat = self._str_servlist()
        d = super().export_data_dict()
        d['environment']['DYNAMIC_SERVER'] = dat
        return d

    def __str__(self) -> str:
        return str(self.export_data_dict())

    def __repr__(self) -> str:
        return repr(self.export_data_dict())

    @classmethod
    def build_default_main_docker(cls, network_name: str, external_port: int, yaml: dict = None):
        dckr = cls.generate_empty(base=network_name, name='nginx', listenport=external_port, internalport=80, yaml=yaml)
        if 'environment' not in dckr._dataDict:
            dckr._dataDict['environment'] = {}
        dckr._dataDict['environment']['DYNAMIC_SERVER'] = ''
        return dckr
