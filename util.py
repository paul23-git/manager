import subprocess
from pathlib import Path
import yaml
import DockerCompose


def chown_as_sudo(file: Path, owner: str, group: str = None, *args, **kwargs):
    owner_str = owner
    if group is not None:
        owner_str = '{owner}:{group}'.format(owner=owner, group=group)
    subprocess.run([
        'sudo',
        'chown',
        *args,
        owner_str,
        file.as_posix(),
    ], check=True)


def test_location(location: Path, overwrite: bool = False, no_overwrite: bool = False) -> bool:
    if location.exists():
        if overwrite:
            return True
        elif no_overwrite:
            raise ValueError('Location already exists')
        else:
            print('{location} already existing.'.format(location=location))
            s = input('Clear build directory? [y, N]')
            if s != 'Y' and s != 'y':
                raise ValueError('Location already exists')
            return True
    return False


def yaml_load(filename: Path) -> dict:
    with open(filename.as_posix(), 'r') as file:
        data = yaml.safe_load(file)
    return data


def load(filename: Path, main_name: str):
    data = yaml_load(filename)
    out = DockerCompose.DockerCompose(data, main_name)
    return out


