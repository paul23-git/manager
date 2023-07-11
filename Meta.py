from functools import cmp_to_key
from pathlib import Path
from typing import Dict, Union, Optional, List, Callable, TypeVar

from ServerData import ServerData
from compile import default_clone, compile_javascript
from exportable_compose_part import ExportableComposePart

P = Union[str, Dict[str, 'P']]


class Meta(ExportableComposePart):
    def export_data_dict(self) -> Union[str, int, dict, None]:
        return self.export_meta()

    def __init__(self, data_dict: Dict[str, Union[str, dict]] = None, main_name: str = None):
        if data_dict is None:
            data_dict = {}
        self.main = main_name if main_name is not None else data_dict['main']
        t = data_dict.get('locations', None)
        all_locs = t if t is not None else {}
        self.locations = {path: ServerData(path, *loc.split(':'))
                          for path, loc in all_locs.items()}  # type: Dict[str, ServerData]
        self.dockerData = data_dict.get('docker_data', {})  # type: Dict[str, P]

    def get_build_environment(self, docker_name: str):
        return self.dockerData[docker_name].get('environment', {})

    def clear_build_environment(self, docker_name: str):
        self.dockerData[docker_name]['environment'] = {}

    def set_build_environment_variable(self, docker_name: str, variable: str, value: str):
        v = self.dockerData[docker_name].get('environment', None)
        if v is None:
            v = {}
            self.dockerData[docker_name]['environment'] = v
        v[variable] = value

    def export_meta(self):
        export = {
            'main': self.main,
            'docker_data': self.dockerData
        }
        if self.locations is not None:
            export['locations'] = {path: '{loc.name}:{loc.port}'.format(loc=loc) for path, loc in
                                   self.locations.items()}
        return export

    def set_docker_code_type(self, docker_name: str, code_type: str):
        if docker_name not in self.dockerData:
            self.dockerData[docker_name] = {}
        self.dockerData[docker_name]['compile-script'] = code_type

    def add_location(self, path: str, name: str, port: int):
        self.locations[path] = ServerData(path, name, port)

    def remove_all_by_server(self, server_name: str):
        rem = [path for (path, loc) in self.locations.items() if loc.name == server_name]
        for path in rem:
            del self.locations[path]

    def get_sorted_locations(self) -> List[ServerData]:
        s = sorted(self.locations.values(),
                   key=cmp_to_key(lambda l, r: 1 if l.is_more_generic(r) else -1)
                   )
        return s

    def get_compile_script(self, docker_name: str) -> Optional[Callable[[Path, Optional[Dict[str, str]]], Path]]:
        try:
            s = {
                'react': compile_javascript,
                'sails': compile_javascript,
                'node': compile_javascript,
                'nginx': compile_javascript,
                'frontend': compile_javascript,
                'backend': compile_javascript,
            }  # type: Dict[str, Callable[[Path], Path]]
            return s[self.dockerData[docker_name]['compile-script']]
        except KeyError:
            return default_clone
