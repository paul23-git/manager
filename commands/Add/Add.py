import typing
from pathlib import Path
from DockerCompose import DockerCompose
from DockerService import DockerService
from builders import make_node_dockerfile, make_nginx_dockerfile
from commands.build_helper import build_reverse_proxy
from git_util import load_git, get_current_branch_name, get_latest_tag, get_current_full_commit_sha


# PathLike = typing.Union[str, bytes, Path]


def add(compose: DockerCompose,
        base_dir: Path,
        name: str,
        git_settings: typing.Sequence[str],
        url_path: typing.List[str],
        build_env: typing.Dict[str, str] = None,
        port: int = 1337,
        new_volumes: typing.Union[typing.Sequence[str], str] = None,
        new_environment_vars: typing.Union[typing.Sequence[str], str] = None,
        yaml: dict = None,
        overwrite: bool = False,
        no_overwrite: bool = False,
        quiet: bool = False,
        version: str = None,
        server_type: str = 'node') -> typing.List[typing.Optional[DockerService]]:
    # Adds a new backend docker to an existing server group
    # branch can be anything from a branch, a tag or a git SHA code
    # The default update behaviour is based on the branch type given:
    # if previous was a branch it will be the latest commit to that branch
    # if previous was a tag/sha it will be that specific tag/sha
    if new_environment_vars is None:
        new_environment_vars = []

    if version is None:
        version = '18' if not yaml else yaml.pop('node_version', '18')
    else:
        if yaml:
            yaml.pop('node_version', '18')

    if version[0] == 'v':
        version = version[1:]
    basename = base_dir.parts[-1]
    fullname = '{basename}.{name}'.format(basename=basename, name=name)
    if fullname in compose.services:
        if not overwrite and not no_overwrite:
            raise ValueError("Docker already existing, do you wish to update instead?")

    location = base_dir / fullname
    if not quiet:
        print('Building dockerfile settings....')
    if not location.exists():
        location.mkdir()
    try:
        # location_build = make_sails_dockerfile(base_dir, fullname, version, overwrite, no_overwrite, quiet)
        make_func = {'node': make_node_dockerfile, 'nginx': make_nginx_dockerfile}[server_type]
        make_func(base_dir, fullname, version, overwrite, no_overwrite, quiet)
    except ValueError:
        if not no_overwrite:
            raise
    if not quiet:
        print('loading from git....')
    location_git = None
    actual_branch = None
    latest_tag = None
    commit = None
    try:
        location_git, retcode = load_git(base_dir, fullname, git_settings, overwrite, no_overwrite, quiet)
        actual_branch = get_current_branch_name(base_dir, fullname)
        latest_tag = get_latest_tag(base_dir, fullname)
        commit = get_current_full_commit_sha(base_dir, fullname)
        try:
            dckr_data = compose.services[fullname]
            dckr_data.set_environment_variable('GIT_BRANCH', actual_branch if actual_branch else "")
            dckr_data.set_environment_variable('GIT_LATEST_TAG', latest_tag if latest_tag else "")
        except KeyError:
            pass
    except ValueError:
        if not no_overwrite:
            raise
    else:
        if retcode is not None and (retcode.returncode != 0 and retcode.returncode != 127):
            raise ValueError("Git failed, creation failed")

    if compose.main_docker is not None:
        try:
            compose.add_server(url_path, fullname, port)
        except ValueError:
            if not quiet:
                print("WARNING: Already in server settings")
            if not no_overwrite and not overwrite:
                raise

    build_reverse_proxy(compose, base_dir, 'portal', overwrite, quiet)

    new_data = None

    if fullname not in compose.services or overwrite:
        if not quiet:
            print('Building docker-compose extension....')
        if yaml is None:
            yaml = {}

        if new_volumes is not None and len(new_volumes) > 0:
            if 'volumes' not in yaml:
                yaml['volumes'] = []
            if isinstance(new_volumes, list):
                yaml['volumes'].extend(new_volumes)
            else:
                yaml['volumes'].append(new_volumes)

        if actual_branch is not None:
            new_environment_vars.append(f'GIT_BRANCH={actual_branch}')
        if latest_tag is not None:
            new_environment_vars.append(f'GIT_LATEST_TAG={latest_tag}')
        if commit is not None:
            new_environment_vars.append(f'GIT_COMMIT={commit}')

        if new_environment_vars is not None and len(new_environment_vars) > 0:
            if 'environment' not in yaml:
                yaml['environment'] = []
            if not isinstance(new_environment_vars, list):
                new_environment_vars = [new_environment_vars]
            if isinstance(yaml['environment'], dict):
                # noinspection PyTypeChecker
                edict = dict([(e.split('=', 1)) for e in new_environment_vars])
                yaml['environment'] = {**yaml['environment'], **edict}
            else:
                yaml['environment'].extend(new_environment_vars)

        new_data = DockerService.generate_empty(basename, name, yaml)

        compose.services[fullname] = new_data
        compose.meta.set_docker_code_type(fullname, server_type)

    if build_env is not None:
        for env in build_env:
            k, v = env.split('=', 1)
            compose.meta.set_build_environment_variable(fullname, k, v)

    if not quiet:
        print("Transpiling javascript....")
    scr = compose.meta.get_compile_script(fullname)
    environment = compose.meta.get_build_environment(fullname)

    if scr is not None:
        scr(location_git, environment)
    else:
        if not quiet:
            print('unknown code, left as is')
    return [new_data, compose.main_docker]


