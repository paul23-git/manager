import getpass
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict

import tail
from docker_util import wait_for_finish, get_exit_code, docker_build, docker_run, docker_remove
import util
from shutil import copyfile


def copy_rsa_keys(build_dir: str= './build-dockers/'):
    home = Path.home().resolve()
    out_rsa_fname = Path(build_dir + 'local/ssh/id_rsa')
    out_rsa_pub_fname = Path(build_dir + 'local/ssh/id_rsa.pub')
    out_known_hosts_fname = Path(build_dir + 'local/ssh/known_hosts')
    in_rsa_fname = home / Path('.ssh/id_rsa')
    in_rsa_pub_fname = home / Path('.ssh/id_rsa.pub')
    in_known_hosts_fname = home / Path('.ssh/known_hosts')
    if not out_rsa_fname.is_file() and in_rsa_fname.is_file():
        copyfile(in_rsa_fname.resolve().as_posix(), out_rsa_fname.resolve().as_posix())
    if not out_rsa_pub_fname.is_file() and in_rsa_pub_fname.is_file():
        copyfile(in_rsa_pub_fname.resolve().as_posix(), out_rsa_pub_fname.resolve().as_posix())
    if not out_known_hosts_fname.is_file() and in_known_hosts_fname.is_file():
        copyfile(in_known_hosts_fname.resolve().as_posix(), out_known_hosts_fname.resolve().as_posix())


def compile_javascript(source: Path, environment_variables: Dict[str, str] = None, ubuntu: bool = False) -> Path:
    # Given already downloaded git source
    # Runs the command `npm run build`
    # Project itself is responsible for building itself into `/build` directory
    # /build directory should include everything, node_modules for backend and html for static frontend
    # Project is given the RSA keys for the git repository as specified in the readme

    print("Javascript build started")
    dest = source / 'build'
    try:
        os.remove('./tmp/cid')
    except FileNotFoundError:
        pass
    if dest.exists():
        shutil.rmtree(dest.as_posix())
    dest.mkdir(parents=True)
    if (source/"node_modules").exists():
        shutil.rmtree((source/"node_modules").as_posix())

    if environment_variables is None:
        environment_variables = {}

    try:
        copy_rsa_keys()
        # copy rsa keys if not existing (dockerfile refers to this directory)
        # note copy, not link a volume to prevent ownership problems with concurrent builds

        dockerfilename = './build-dockers/Dockerfile-build'
        if not ubuntu:
            dockerfilename += '-alpine'
        image = docker_build(Path(dockerfilename).resolve(),
                             'spiderweb-builder')

        code = docker_run(image, '-it',
                          temporary=False,
                          volume=[
                              '{host}:/javascript'.format(host=source.resolve().as_posix()),
                              '{home}/.npm:/home/node/.npm'.format(home=Path.home().resolve().as_posix()),
                          ],
                          environment=environment_variables,
                          cidfile='./tmp/cid')
        with open('./tmp/cid') as f:
            docker_id = tail.tail(f, 1)
        try:
            wait_for_finish(docker_id, 1)
            docker_remove(docker_id)
            if get_exit_code(docker_id) != '0':
                raise RuntimeError('Cannot build')
        except subprocess.CalledProcessError:
            pass
    finally:
        usr = getpass.getuser()
        group = os.getegid()
        util.chown_as_sudo(source, usr, str(group), '-R')

    return dest


def default_clone(source: Path) -> Path:
    print("Default, clone all code")
    dest = source / 'build'
    if dest.exists():
        shutil.rmtree(dest.as_posix())
    dest.mkdir(parents=True)
    shutil.copytree(source.as_posix(),
                    (source / 'build').as_posix(),
                    ignore=shutil.ignore_patterns('build/*', 'build'))
    return dest
