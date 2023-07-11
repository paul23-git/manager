import shutil
import subprocess
from pathlib import Path
from typing import List

from DockerCompose import DockerCompose
from DockerService import DockerService
from docker_util import docker_remove


def remove_docker(fullname: str):
    try:
        docker_remove(fullname, True)
    except subprocess.CalledProcessError:
        pass



def remove_data(base_dir: Path,
                dckr: DockerService):
    try:
        path = dckr.get_source_path()
        fpath = (base_dir / path).resolve()
        shutil.rmtree(fpath.as_posix())
    except KeyError:
        pass


def clean_compose(compose: DockerCompose,
                  fullname: str,
                  clean_path: bool = True,
                  quiet: bool = False):
    compose.remove_docker(fullname)

    if clean_path:
        if not quiet:
            print("cleaning up main docker....")
        compose.remove_server(fullname)


def remove(compose: DockerCompose,
           base_dir: Path,
           name: str,
           clean_path: bool = False,
           quiet: bool = False) -> List[DockerService]:
    # Removes a container from the network
    # While not required clean_path you typically wish to set to True
    basename = base_dir.parts[-1]
    fullname = '{basename}.{name}'.format(basename=basename, name=name)
    dckr = compose.get_docker(fullname)

    if dckr == compose.main_docker:
        raise KeyError("Cannot remove main docker, use purge instead")

    if dckr is None:
        print("Docker {fullname} not found".format(fullname=fullname))

    if not quiet:
        print("removing docker {fullname}...".format(fullname=fullname))
    if dckr is not None:
        remove_docker(fullname)
        remove_data(base_dir, dckr)
    clean_compose(compose, fullname, clean_path, quiet)

    r = []
    if clean_path:
        r.append(compose.main_docker)
    return r
