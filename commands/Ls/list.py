import os
import sys
import typing
from pathlib import Path
from subprocess import CalledProcessError

from tabulate import tabulate

from DockerCompose import DockerCompose
from DockerService import DockerService
from git_util import get_current_short_commit_sha, get_current_branch_name
from util import load


def list_dockers(compose: DockerCompose,
                 base_dir: Path) -> None:
    # list all dockers which belong to a group
    # Together with the branch/tag/sha used for building
    # as well as the actual git sha for the server
    names = compose.get_all_docker_names()
    data: typing.List[typing.List[str]] = []
    for name in names:
        docker = compose.get_docker(name)  # type: typing.Optional[DockerService]
        if docker is not None:
            branch = ""
            sha = ""
            name = docker.get_fullname()
            sys.stdout.write("\033[K")
            print(f'Checking repository for {name} ...', end='\r')
            try:
                branch = get_current_branch_name(base_dir, name)
            except CalledProcessError:
                pass
            try:
                os.remove('./tmp/git-cid')
            except FileNotFoundError:
                pass
            try:
                sha = get_current_short_commit_sha(base_dir, name)
            except CalledProcessError:
                pass
            d = [name, branch if branch is not None else "", sha if sha is not None else ""]
            data.append(d)
            #print(len(f'Checking repository for {name} ...')*' ', end='\r')

    sys.stdout.write("\033[K")
    print(tabulate(data, headers=['name', 'branch', 'git sha']))


if __name__ == "__main__":
    test_directory = Path('/home/paul/webasupport/dockers/builder/dockers/allsports.test')
    rev_proxy = 'allsports.test.nginx'
    dckr_cmp = load((test_directory / 'docker-compose.yml').resolve(), rev_proxy)
    list_dockers(dckr_cmp, test_directory.resolve())