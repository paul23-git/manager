import os
import typing

import yaml
import argparse
from pathlib import Path

import util
from commands.Add.Add import add
from commands.Create.Create import create
from commands.Purge.Purge import purge
from commands.Rebuild_portal.Rebuild import rebuild
from commands.Reload.Reload import reload
from commands.Remove.Remove import remove
from commands.Update.Update import update
from docker_util import docker_compose_up
from git_util import get_current_branch_name

from DockerCompose import DockerCompose
import subprocess

from commands.Ls.list import list_dockers

PathLike = typing.Union[str, bytes, Path]


def write(filename: Path, data: DockerCompose):
    converted_data = data.export_data_dict()
    with open(filename.as_posix(), 'w+') as file:
        yaml.safe_dump(converted_data, file)


class WritableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError("dir:{0} is not a valid path".format(prospective_dir))
        if os.access(prospective_dir, os.F_OK | os.R_OK | os.W_OK):
            setattr(namespace, self.dest, Path(prospective_dir).resolve())
        else:
            raise argparse.ArgumentTypeError("dir:{0} is not writable".format(prospective_dir))


class IsDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        setattr(namespace, self.dest, Path(prospective_dir))


def parse_input() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Modify docker container definitions')
    parser.add_argument('directory', action=IsDir, help="Project/Network directory")
    subparsers = parser.add_subparsers(help="Command to execute", dest='cmd')
    parser.add_argument('--reverse-proxy', help="Name of the reverse proxy docker")
    parser.add_argument('--no-launch', default=False, action='store_true',
                        help="Only update docker compose and files, do not update running dockers")
    parser.add_argument('-q', '--quiet', default=False, action='store_true', help="Less user interaction")
    parser.add_argument('-o', '--overwrite', help='Force overwriting existing docker', action='store_true',
                        dest='overwrite')
    parser.add_argument('--no-overwrite', help='Force continuation on existing docker', action='store_true')

    add = subparsers.add_parser('add', help='Add a container')
    add.add_argument('docker', help='New docker name')
    add.add_argument('git', help='Git repository')
    add.add_argument('--branch', default='production', help='branch or tag from where to clone')
    add.add_argument('--url-path', action='append', help='path to connect to the server')
    add.add_argument('--port', default=1337, help='Port docker uses internally')
    add.add_argument('--yaml', help='Yaml settings for service')
    add.add_argument('--server-type', choices=['node', 'nginx'], help='Server type to use', default='node')
    add.add_argument('--node-version', '--version', help='Server version to use', default='18')
    add.add_argument('-v', help='Volume for new docker container', action='append', dest='volumes')
    add.add_argument('-e', help='Environment variable for new docker container', action='append',
                     dest='environment_variables')
    add.add_argument('--build-env', help='Environment variable during build', action='append',
                     dest='build_environment_variables')

    rebuild = subparsers.add_parser('rebuild-portal', help='Rebuild nginx reverse proxy')

    purge = subparsers.add_parser('purge', help='Purge full system')
    purge.add_argument('-f', '--force', help="Forcibly remove managed networks", default=False, action='store_true', )

    create = subparsers.add_parser('create', help='Create a network group')
    create.add_argument('--network', help='New network name')
    create.add_argument('-p', '--port', help='New network port')
    create.add_argument('git', help='Git repository of frontend')
    create.add_argument('--branch', default='production', help='branch or tag from where to clone')
    create.add_argument('--build-env', help='Environment variable during build', action='append',
                        dest='build_environment_variables')
    create.add_argument('--overwrite', help='Overwrite existing dockers', action='store_true', default=False)
    create.add_argument('-e', help='Environment variable for new docker container', action='append',
                        dest='environment_variables')
    create.add_argument('--yaml', help='Yaml settings for frontend service')

    remove = subparsers.add_parser('remove', help='Remove a container')
    remove.add_argument('docker', help='Docker name')
    remove.add_argument('-c', '--clean', action='store_true', default=False, help='Clean reverse proxy', dest='clean')

    update = subparsers.add_parser('update', help='Update a container code')
    update.add_argument('docker', help='Docker container name', nargs='*')
    update.add_argument('--git', help='Git repository')
    update.add_argument('--branch',
                        help='branch or tag from where to clone, if not given same branch as existing code is used')

    reload = subparsers.add_parser('reload', help='Reload settings')
    reload.add_argument('docker', help='Docker container name')
    reload.add_argument('--yaml', help='Yaml settings for docker service')
    reload.add_argument('-v', help='Volume for new docker container', action='append', dest='volumes')
    reload.add_argument('-e', help='Environment variable for new docker container', action='append',
                        dest='environment_variables')
    reload.add_argument('-f', '--forced', help='Force rebuilding of all dockers upon loading', action='store_true',
                        dest='forced')

    list_dockers = subparsers.add_parser('ls', help='List all containers')

    parsed = parser.parse_args()
    basename = parsed.directory.parts[-1]
    parsed.reverse_proxy = parsed.reverse_proxy if parsed.reverse_proxy else basename + '.nginx'
    if parsed.cmd == 'add':
        parsed.url_path = parsed.url_path if parsed.url_path else ['/api/{docker}'.format(docker=parsed.docker)]

    if parsed.cmd == 'create':
        if parsed.network is not None and ':' in parsed.network:
            v = parsed.network.split()
            parsed.network = v[0]
            if not parsed.port:
                parsed.port = v[1]
        if parsed.port is None:
            parsed.port = 80
    return parsed


def update_helper(comp: DockerCompose, args):
    git_args = []
    if args.git is not None:
        git_args = [args.git]

    git_args.extend(['--depth', '1'])
    dockers = set()
    for name in args.docker:
        print('==== {name} ===='.format(name=name))
        if args.branch:
            branch = args.branch
        else:
            basename = args.directory.parts[-1]
            fullname = '{basename}.{name}'.format(basename=basename, name=name)
            branch = get_current_branch_name(args.directory, fullname)
            if branch is not None:
                print('found branch: {branch}'.format(branch=branch))
            else:
                branch = 'production'
        dockers.update(update(
            compose=comp,
            base_dir=args.directory,
            name=name,
            branch=branch,
            git_settings=git_args,
            quiet=args.quiet,
        ))
    if len(dockers) > 0:
        write(args.directory / 'docker-compose.yml', comp)
    return list(dockers)


def add_helper(comp: DockerCompose, args: argparse.Namespace):
    git_args = [args.git, '--depth', '1']
    if args.branch:
        git_args.extend(['--branch', '{branch}'.format(branch=args.branch)])
    dockers = add(
        compose=comp,
        base_dir=args.directory.resolve(),
        name=args.docker,
        git_settings=git_args,
        url_path=args.url_path,
        port=args.port,
        yaml=util.yaml_load(Path(args.yaml)) if args.yaml else None,
        new_volumes=args.volumes,
        new_environment_vars=args.environment_variables,
        overwrite=args.overwrite,
        no_overwrite=args.no_overwrite,
        version=args.node_version,
        server_type=args.server_type,
        build_env=args.build_environment_variables,
        quiet=args.quiet)
    write(args.directory / 'docker-compose.yml', comp)
    return dockers


def create_helper(comp: DockerCompose, args):
    n = args.directory if args.network is None else (args.directory / args.network)  # type: Path
    n.mkdir(parents=True, exist_ok=True)
    n = n.resolve()
    git_args = [args.git, '--depth', '1']
    if args.branch:
        git_args.extend(['--branch', '{branch}'.format(branch=args.branch)]),
    comp, dockers = create(
        directory=n,
        port=args.port,
        overwrite=args.overwrite,
        git_settings=git_args,
        quiet=args.quiet,
        build_env=args.build_environment_variables,
        yaml=util.yaml_load(Path(args.yaml)) if args.yaml else None,
        run_env=args.environment_variables,
    )
    write(n / 'docker-compose.yml', comp)
    return dockers


def remove_helper(comp: DockerCompose, args):
    dockers = remove(compose=comp,
                     base_dir=args.directory.resolve(),
                     name=args.docker,
                     clean_path=args.clean,
                     quiet=args.quiet)
    if dockers is not None:
        write(args.directory / 'docker-compose.yml', comp)
    return dockers


def reload_helper(comp: DockerCompose, args):
    dockers = reload(
        compose=comp,
        name=args.docker,
        base_dir=args.directory.resolve(),
        yaml=util.yaml_load(Path(args.yaml)) if args.yaml else None,
        new_volumes=args.volumes,
        new_environment_vars=args.environment_variables,
        quiet=args.quiet)
    if dockers is not None:
        write(args.directory / 'docker-compose.yml', comp)
    return dockers if not args.forced else None


def rebuild_helper(comp: DockerCompose, args):
    rebuild(
        compose=comp,
        base_dir=args.directory.resolve(),
        overwrite=args.overwrite,
        quiet=args.quiet,
    )
    return [comp.main_docker] if comp.main_docker is not None else None


def purge_helper(comp: DockerCompose, args):
    purge(
        compose=comp,
        base_dir=args.directory.resolve(),
        forced=args.force,
        quiet=args.quiet,
    )
    return [comp.main_docker] if comp.main_docker is not None else None


def list_docker_helper(comp: DockerCompose, args):
    list_dockers(
        compose=comp,
        base_dir=args.directory.resolve())


def main():
    args = parse_input()
    basename = args.directory.parts[-1]
    print('Working on group {basename}'.format(basename=basename))
    dat = util.load(args.directory / 'docker-compose.yml', args.reverse_proxy) if args.cmd != 'create' else None

    cmd_dict = {
        'add': add_helper,
        'create': create_helper,
        'update': update_helper,
        'remove': remove_helper,
        'reload': reload_helper,
        'rebuild-portal': rebuild_helper,
        'purge': purge_helper,
        'ls': list_docker_helper,
    }
    dockers = cmd_dict[args.cmd](dat, args)
    no_change_list = ['purge', 'ls']

    # if command returned dockers the dockers will be rebuild as final step to release a new version
    if not args.no_launch and args.cmd not in no_change_list:
        print('Docker containers updating')
        docker_compose_up(dockers, args.directory)
    return


if __name__ == "__main__":
    main()
