import typing
from typing import Dict, Union, List

from DockerService import DockerService, MainDocker
from Meta import Meta
from exportable_compose_part import ExportableComposePart


class DockerCompose(ExportableComposePart):
    # Defines and allows interacting to the docker compose file.
    def __init__(self,
                 data_dict: Dict[str, Union[dict, str]] = None,
                 main_name: str = None,
                 network_name: str = None,
                 network_port: int = None,
                 yaml: dict = None,
                 *args, **kwargs):
        def load_dckr(dckr: Dict[str, dict]) -> (Dict[str, DockerService], MainDocker):
            ret = {}  # type: Dict[str, DockerService]
            main = None
            for n, docker in dckr.items():
                if n != main_name:
                    ret[n] = DockerService(docker)
                else:
                    main = MainDocker(docker)
                    ret[n] = main
            return ret, main

        if data_dict:
            self.version = data_dict['version']  # type: str
            self.networks = data_dict['networks']
            self.services, self.main_docker = load_dckr(data_dict['services'])
            self.meta = Meta(data_dict['x-meta'])
        else:
            if not network_name or not network_port:
                raise ValueError('Both data_dict and nework_name/port are empty')
            self.version = '3.7'
            self.networks = {
                network_name: {"driver": "bridge"}
            }
            self.services = {}
            self.main_docker = MainDocker.build_default_main_docker(network_name, network_port, yaml)
            redis_docker = DockerService.generate_empty(network_name, 'redis')
            self.services = {
                self.main_docker.get_fullname(): self.main_docker,
                redis_docker.get_fullname(): redis_docker,
            }
            self.meta = Meta(main_name=self.main_docker.get_fullname())
            self.meta.set_docker_code_type(self.main_docker.get_fullname(), 'react')

    def export_data_dict(self):
        return {
            "version": self.version,
            "networks": self.networks,
            "services": {n: d.export_data_dict() for n, d in self.services.items()},
            "x-meta": self.meta.export_data_dict(),
        }

    def add_server(self, path: List[str], server_name: str, server_port: int):
        for p in path:
            self.main_docker.add_server(p, server_name, server_port)
            self.meta.add_location(p, server_name, server_port)

    def get_docker(self, name) -> typing.Optional[DockerService]:
        return self.services.get(name)

    def get_all_docker_names(self):
        return self.services.keys()

    def get_all_git_docker_names(self):
        p = Union[str, Dict[str, 'P']]

        def is_git(dat: Dict[str, p]) -> bool:
            return dat.get('compile_script') is not None

        return (k for k, v in self.meta.dockerData.items() if is_git(v))

    def remove_docker(self, name):
        try:
            del self.services[name]
        except KeyError:
            pass
        try:
            del self.meta.dockerData[name]
        except KeyError:
            pass

    def remove_server(self, server_name: str):
        self.main_docker.remove_server(server_name)
        self.meta.remove_all_by_server(server_name)

    def __str__(self):
        return str(self.export_data_dict())

    def __repr__(self):
        return repr(self.export_data_dict())
