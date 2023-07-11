import os
import shutil
from pathlib import Path
from typing import Sequence, Optional, List, Dict, Union

from DockerCompose import DockerCompose
from DockerService import DockerService
from builders import make_nginx_dockerfile, make_redis_dockerfile
from commands.build_helper import build_reverse_proxy
from git_util import load_git, get_current_branch_name, get_latest_tag, get_current_full_commit_sha


def create(directory: Path,
           port: int = None,
           git_settings: Sequence[str] = None,
           build_env: Dict[str, str] = None,
           run_env: Union[Sequence[str], str] = None,
           overwrite: bool = False,
           yaml: dict = None,
           quiet: bool = False) -> (DockerCompose, List[Optional[DockerService]]):
    # Create a new server group
    # Always adds an nginx frontend
    if run_env is None:
        run_env = []
    if git_settings is None:
        git_settings = []
    if yaml is None:
        yaml = {}

    name = directory.parts[-1]
    base = directory.parts[:-1]
    fullname = "{name}.nginx".format(name=name)

    print("copying files....")
    if directory.exists() and os.listdir(directory.as_posix()):
        if overwrite:
            print('removing dir')
            shutil.rmtree(directory.as_posix())
        else:
            raise ValueError('Directory not empty')
    if not directory.exists():
        directory.mkdir(parents=True)

    make_nginx_dockerfile(directory, "{name}.nginx".format(name=name))
    make_redis_dockerfile(directory, "{name}.redis".format(name=name))


    if run_env is not None and len(run_env) > 0:
        if 'environment' not in yaml:
            yaml['environment'] = []
        if not isinstance(run_env, list):
            run_env = [run_env]
        if isinstance(yaml['environment'], dict):
            # noinspection PyTypeChecker
            edict = dict([(e.split('=', 1)) for e in run_env])
            yaml['environment'] = {**yaml['environment'], **edict}
        else:
            yaml['environment'].extend(run_env)

    if not quiet:
        print("Loading git....")


    location_git, retcode = load_git(directory, "{name}.nginx".format(name=name), git_settings, overwrite, False, quiet)
    if retcode.returncode != 0:
        raise ValueError("Git failed, creation failed")

    if not quiet:
        print("generating compose file....")
    compose = DockerCompose(network_name=name, network_port=port, yaml=yaml)


    actual_branch = get_current_branch_name(directory, fullname)
    latest_tag = get_latest_tag(directory, fullname)
    commit = get_current_full_commit_sha(directory, fullname)

    if build_env is not None:
        for env in build_env:
            k, v = env.split('=', 1)
            compose.meta.set_build_environment_variable("{name}.nginx".format(name=name), k, v)

    if not quiet:
        print("Transpiling javascript....")
    scr = compose.meta.get_compile_script("{name}.nginx".format(name=name))
    environment = compose.meta.get_build_environment("{name}.nginx".format(name=name))

    if scr is not None:
        scr(location_git, environment)
    else:
        if not quiet:
            print('unknown code, left as is')

    build_reverse_proxy(compose, directory, 'portal', overwrite, quiet)

    dckr = compose.get_docker(fullname)
    if dckr is not None:
        if commit is not None:
            dckr.set_environment_variable('GIT_COMMIT', commit)
        if actual_branch is not None:
            dckr.set_environment_variable('GIT_BRANCH', actual_branch)
        if latest_tag is not None:
            dckr.set_environment_variable('GIT_LATEST_TAG', latest_tag)

    return compose, list(compose.services.values())


if __name__ == '__main__':
    path = Path('../../dockers/bondinet.app').resolve()
    compose = create(directory=path,
                     port=280,
                     git_settings=['ssh://git@gitlab.webasupport.com:1122/P_0326_BN/frontend.git',
                                   '--single-branch',
                                   '--depth', '1'],
                     overwrite=True,
                     quiet=False)
    print(compose)
