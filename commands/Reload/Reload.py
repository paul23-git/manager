from pathlib import Path
from typing import Sequence, Union, List, Optional

from DockerCompose import DockerCompose
from DockerService import DockerService


def reload(compose: DockerCompose,
           base_dir: Path,
           name: str,
           new_volumes: Union[Sequence[str], str] = None,
           new_environment_vars: Union[Sequence[str], str] = None,
           yaml: dict = None,
           quiet: bool = False) -> List[Optional[DockerService]]:
    # Reloads a docker int the network
    # Allowing new settings in yaml/environement/volumes without downloading and compiling code
    basename = base_dir.parts[-1]
    fullname = '{basename}.{name}'.format(basename=basename, name=name)
    dckr = compose.get_docker(fullname)

    if dckr is None:
        raise KeyError("Docker {fullname} not found".format(fullname=fullname))

    if not quiet:
        print('Building docker-compose extension....')
    if yaml is None:
        yaml = {}

    if new_volumes is not None and len(new_volumes) > 0:
        if 'volumes' not in yaml:
            yaml['volumes'] = []
        if isinstance(new_volumes, list):
            yaml['volumes'].extend(new_volumes)
        else:
            yaml['volumes'].append(new_volumes)

    if new_environment_vars is not None and len(new_environment_vars) > 0:
        if 'environment' not in yaml:
            yaml['environment'] = []

        if not isinstance(new_environment_vars, list):
            new_environment_vars = [new_environment_vars]
        if isinstance(yaml['environment'], dict):
            edict = dict([(e.split('=', 1)) for e in new_environment_vars])
            yaml['environment'] = {**yaml['environment'], **edict}
        else:
            yaml['environment'].extend(new_environment_vars)
            d = dict(e.split('=', 1) for e in yaml['environment'])
            yaml['environment'] = ['{k}={v}'.format(k=k, v=v) for k,v in d.items()]

    if dckr is compose.main_docker:
        if 'environment' not in yaml:
            yaml['environment'] = []

    dckr.merge_data(yaml)

    return [dckr]
