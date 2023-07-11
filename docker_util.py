import itertools
import json
import re
import subprocess
import time
import typing
from pathlib import Path

from DockerService import DockerService


def wait_for_finish(docker_ident: str, sleeptime=0.5) -> None:
    status = get_status(docker_ident)
    while status == 'running':
        time.sleep(sleeptime)
        status = get_status(docker_ident)
    return


def get_status(docker_ident: str) -> str:
    return docker_inspect(docker_ident, '{{.State.Status}}')


def docker_inspect(docker_ident: str, go_template: str = None) -> str:
    cmd = ['sudo', 'docker', 'inspect', docker_ident]
    if go_template is not None:
        cmd.append('--format=\'{go_template}\''.format(go_template=go_template))
    res = subprocess.check_output(cmd, universal_newlines=True)
    m = re.search('\'?(.+?)\'?\\n?$', res)
    return m.group(1)


def docker_network_inspect(network_ident: str, go_template: str = None) -> str:
    cmd = ['sudo', 'docker', 'network', 'inspect', network_ident]
    if go_template is not None:
        cmd.append('--format=\'{go_template}\''.format(go_template=go_template))
    res = subprocess.check_output(cmd, universal_newlines=True)
    m = re.search('\'?(.+?)\'?\\n?$', res)
    return m.group(1)


def get_exit_code(docker_ident: str) -> str:
    return docker_inspect(docker_ident, '{{.State.ExitCode}}')


def get_containers_in_network(network_ident: str) -> typing.KeysView[str]:
    containers_json_string = docker_network_inspect(network_ident, '{{json .Containers}}')
    d = json.loads(containers_json_string)
    return d.keys()


def get_networks_from_container(container_ident: str) -> typing.KeysView[str]:
    containers_json_string = docker_inspect(container_ident, '{{json .NetworkSettings.Networks}}')
    d = json.loads(containers_json_string)
    return d.keys()


def network_remove(*network_ids: str):
    cmd = ['sudo', 'docker', 'network', 'rm', *network_ids]
    subprocess.run(cmd, check=True)


def convert_kwargs(**kwargs: typing.Union[typing.List[str], str]) \
        -> typing.Generator[str, typing.Any, None]:
    def convert_single(k: str, v: str) -> str:
        return '--{key}={value}'.format(key=k, value=v)

    for key, value in kwargs.items():
        if isinstance(value, str):
            yield convert_single(key, value)
        else:
            yield from (convert_single(key, v) for v in value)


def docker_pull(name: str):
    subprocess.run(['sudo', 'docker', 'pull', '-q', name], check=True)


def docker_remove(docker: str, forced: bool = False):
    opt = []
    if forced:
        opt.append('-f')
    subprocess.run(['sudo', 'docker', 'rm', *opt, docker], check=True)


def docker_run(docker_image: str,
               *args: str,
               temporary: bool = True,
               docker_args: typing.Optional[typing.Union[str, typing.List[str]]] = None,
               environment: typing.Dict[str, str] = None,
               stdout: typing.Union[int, None, typing.IO] = None,
               fail_on_nonzero_exit: bool = True,
               **kwargs: typing.Union[str, typing.List[str]]) \
        -> subprocess.CompletedProcess:
    if isinstance(docker_args, str):
        a = [docker_args]
    else:
        a = docker_args
    if temporary:
        args = itertools.chain(args, ['--rm'])

    build_envs = itertools.chain.from_iterable(['-e', '{k}={v}'.format(k=k, v=v)] for k, v in environment.items()) \
        if environment is not None else []

    converted_kwargs = convert_kwargs(**kwargs)
    all_args = ['sudo', 'docker', 'run',
                *args, *build_envs, *converted_kwargs,
                docker_image, *(a if a is not None else [])]
    proc = subprocess.run(args=all_args, check=fail_on_nonzero_exit, stdout=stdout)
    # proc = subprocess.run(['echo', 'test'], check=fail_on_nonzero_exit, stdout=stdout)
    return proc


def docker_build(dockerfile_fname: Path, tag: str, *args: str, **kwargs: typing.Union[typing.List[str], str]) -> str:
    converted_kwargs = convert_kwargs(**kwargs)

    if dockerfile_fname.is_file():
        directory = dockerfile_fname.parent
        converted_kwargs = itertools.chain(converted_kwargs,
                                           ['--file={dockerfile_fname}'.format(dockerfile_fname=dockerfile_fname)])
    else:
        directory = dockerfile_fname
    image = subprocess.check_output(['sudo', 'docker', 'build',
                                     directory.as_posix(), '-t', tag, '-q',
                                     *args, *converted_kwargs], universal_newlines=True)
    image = re.search('\'?([^\\n\']+)\'?\\n?', image)
    return image.group(1)


def docker_compose_up(dockers: typing.List[DockerService], directory: Path):
    settings = [
        '--build', '-d', '--remove-orphans',
    ]  # type: typing.List[str]
    if dockers:
        settings.extend(docker.get_fullname() for docker in dockers if docker is not None)
    process = subprocess.run(['sudo', 'docker-compose', 'up', *settings],
                             cwd=directory.as_posix())
