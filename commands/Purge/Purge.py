import os
from pathlib import Path

from DockerCompose import DockerCompose
from commands.Remove.Remove import remove_docker
from docker_util import get_networks_from_container, get_containers_in_network, network_remove


def purge(compose: DockerCompose,
          base_dir: Path,
          forced: bool = False,
          quiet: bool = False):
    # Cleans up a full docker system
    main_dckr = compose.main_docker
    if main_dckr is None:
        raise KeyError("Main docker is none, empty network?")

    for dckr in list(compose.services.values()):
        if dckr is main_dckr:
            continue
        fullname = dckr.get_fullname()
        try:
            remove_docker(fullname)
        except FileNotFoundError as err:
            print(err)

    networks = get_networks_from_container(main_dckr.get_fullname())

    remove_docker(main_dckr.get_fullname())

    toremove = []
    for network in networks:
        if forced or len(get_containers_in_network(network)) <= 0:
            toremove.append(network)
        else:
            print("Network {network} cannot be removed automatically;\n"
                  "\tthere are non-managed docker containers attached to this network"
                  .format(network=network))

    network_remove(*toremove)

    (base_dir / 'docker-compose.yml').unlink()
    if not os.listdir(base_dir.as_posix()):
        base_dir.rmdir()
