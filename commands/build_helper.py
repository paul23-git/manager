from pathlib import Path

from DockerCompose import DockerCompose
from nginx_util import build_nginx_configuration


def build_reverse_proxy(compose: DockerCompose,
                        base_dir: Path,
                        portal_fname: str = 'portal',
                        overwrite: bool = False,
                        quiet: bool = False, ):
    if compose.main_docker is not None:
        if not quiet:
            print('Building main docker....')
        build_nginx_configuration(base_dir,
                                  compose.main_docker.get_fullname(),
                                  portal_fname,
                                  compose.meta.get_sorted_locations(),
                                  overwrite,
                                  quiet)
        if not quiet:
            print('Building main docker.... complete!')
    else:
        if not quiet:
            print("Main docker not found")
