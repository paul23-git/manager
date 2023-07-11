from pathlib import Path

from DockerCompose import DockerCompose
from commands.build_helper import build_reverse_proxy
from nginx_util import build_nginx_configuration


def rebuild(compose: DockerCompose,
            base_dir: Path,
            portal_fname: str = 'portal',
            overwrite: bool = False,
            quiet: bool = False, ):
    # (Re)Builds the main frontend nginx server docker
    build_reverse_proxy(compose, base_dir, portal_fname, overwrite, quiet)
