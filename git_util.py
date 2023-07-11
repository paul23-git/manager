import getpass
import itertools
import os
import re
import shutil
import subprocess
import tempfile
import typing
from pathlib import Path
from typing import Sequence, Optional

import tail
from docker_util import docker_run, wait_for_finish, docker_remove
from util import test_location, chown_as_sudo


def git_docker_run(git_location: Path,
                   git_args: typing.Iterable[str],
                   nosafefix: bool = False,
                   get_output: bool = False) \
        -> (subprocess.CompletedProcess, typing.Union[str, None]):

    if nosafefix:
        docker_args = ['sh', '-c', "git config --global --add safe.directory /git && git " + ' '.join(git_args)]
    else:
        docker_args = ['sh', '-c', "git " + ' '.join(git_args)]

    output = None
    with tempfile.TemporaryFile() as out_file:
        retcode = docker_run('bitnami/git', '-it',
                             '--workdir=/git',
                             volume=[
                                 '{host}:/git'.format(host=git_location.resolve().as_posix()),
                                 '{home}/:/root/'.format(home=Path.home().resolve().as_posix()),
                             ],
                             docker_args=docker_args,
                             cidfile='./tmp/git-cid',
                             stdout=out_file if get_output else None,
                             fail_on_nonzero_exit=False,
                             )
        if get_output:
            out_file.seek(0)
            output = out_file.read().decode('utf-8').strip()

    return retcode, output


def load_git(base_dir: Path,
             name: str,
             git_settings: typing.Iterable[str],
             overwrite: bool = False,
             no_overwrite: bool = False,
             quiet: bool = False) -> (Path, subprocess.CompletedProcess):
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / name / 'javascript'
    if test_location(location, overwrite, quiet or no_overwrite):
        shutil.rmtree(location.as_posix())

    settings = list(git_settings)
    if all(re.fullmatch('--depth', elem) is None for elem in git_settings):
        settings.extend(['--depth', '1'])

    if not quiet:
        print('Loading git into {location}'.format(location=location))
    try:
        retcode, _ = git_docker_run(base_dir / name, git_args=['clone', *settings, 'javascript'], nosafefix=True)
        with open('./tmp/git-cid') as f:
            docker_id = tail.tail(f, 1)
        try:
            wait_for_finish(docker_id, 1)
            docker_remove(docker_id)
        except subprocess.CalledProcessError:
            pass
    finally:
        usr = getpass.getuser()
        group = os.getegid()
        chown_as_sudo(base_dir, usr, str(group), '-R')
    return location, retcode


def clean_update(base_dir: Path,
                 name: str,
                 git_settings: typing.Sequence[str] = None,
                 quiet: bool = False):
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / name / 'javascript'
    backup_location = base_dir / name / 'javascript_backup'
    url = None
    if location.exists():
        url = get_remote_url(base_dir, name)
    if url is None:
        raise RuntimeError('Existing git not found')

    settings = itertools.chain([url], git_settings)

    doing_backup = False
    if location.exists():
        if backup_location.exists():
            shutil.rmtree(backup_location.as_posix())
        shutil.move(location.as_posix(), backup_location.as_posix())
        doing_backup = True

    try:
        _, ret_code = load_git(base_dir, name, settings, True, False, quiet)
    except Exception:
        if backup_location.exists() and doing_backup:
            print('Restoring backup')
            if location.exists():
                shutil.rmtree(location.as_posix())
            shutil.move(backup_location.as_posix(), location.as_posix())
        raise
    else:
        if ret_code.returncode != 0:
            if backup_location.exists() and doing_backup:
                if location.exists():
                    shutil.rmtree(location.as_posix())
                shutil.move(backup_location.as_posix(), location.as_posix())
            raise ValueError("Git failed")
    return ret_code


def update_git(base_dir: Path,
               name: str,
               branch: str = None,
               git_settings: typing.Sequence[str] = None,
               quiet: bool = False):
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / name / 'javascript'

    if branch is not None:
        settings = ['-b', branch]

        if git_settings is not None:
            settings.extend(git_settings)

        return clean_update(base_dir, name, settings, quiet)

    settings = list(git_settings)
    if all(re.fullmatch('--depth', elem) is None for elem in settings):
        settings.extend(['--depth', '1'])

    if not quiet:
        print('Loading git into {location}'.format(location=location))
    try:

        retcode, _ = git_docker_run(location, git_args=['fetch', 'origin', *settings], get_output=True)

        with open('./tmp/git-cid') as f:
            docker_id = tail.tail(f, 1)
        try:
            wait_for_finish(docker_id, 1)
            docker_remove(docker_id)
        except subprocess.CalledProcessError:
            pass
    finally:
        usr = getpass.getuser()
        group = os.getegid()
        chown_as_sudo(base_dir, usr, str(group), '-R')
    return retcode


def get_current_branch_name(base_dir: Path, fullname: str) -> typing.Optional[str]:
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / fullname / 'javascript'

    proc, stdout = git_docker_run(location, git_args=['rev-parse', '--abbrev-ref', 'HEAD'], get_output=True)

    if proc.returncode != 0:
        res = None
    elif stdout is not None:
        res = stdout
    else:
        res = None

    if proc.returncode == 0:
        try:
            os.remove('./tmp/git-cid')
        except FileNotFoundError:
            pass

    return res


def get_current_full_commit_sha(base_dir: Path, fullname: str) -> typing.Optional[str]:
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / fullname / 'javascript'
    proc, stdout = git_docker_run(location, git_args=['rev-parse', 'HEAD'], get_output=True)

    if proc.returncode != 0:
        res = None
    elif stdout is not None:
        res = stdout
    else:
        res = None

    if proc.returncode == 0:
        try:
            os.remove('./tmp/git-cid')
        except FileNotFoundError:
            pass

    return res


def get_current_short_commit_sha(base_dir: Path, fullname: str) -> typing.Optional[str]:
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / fullname / 'javascript'
    proc, stdout = git_docker_run(location, git_args=['rev-parse', '--short', 'HEAD'], get_output=True)

    if proc.returncode != 0:
        res = None
    elif stdout is not None:
        res = stdout
    else:
        res = None

    if proc.returncode == 0:
        try:
            os.remove('./tmp/git-cid')
        except FileNotFoundError:
            pass

    return res


def get_latest_tag(base_dir: Path, fullname: str) -> typing.Optional[str]:
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / fullname / 'javascript'
    proc, stdout = git_docker_run(location, git_args=['describe', '--tags', '--always'], get_output=True)

    if proc.returncode != 0:
        res = None
    elif stdout is not None:
        res = stdout
        if res is not None and res.startswith("fatal"):
            res = ""
    else:
        res = None

    return res


def get_remote_url(base_dir: Path, fullname: str) -> typing.Optional[str]:
    try:
        os.remove('./tmp/git-cid')
    except FileNotFoundError:
        pass
    location = base_dir / fullname / 'javascript'
    proc, stdout = git_docker_run(location, git_args=['remote', 'get-url', 'origin'], get_output=True, nosafefix=True)

    if proc.returncode != 0:
        res = None
    elif stdout is not None:
        res = stdout
    else:
        res = None

    return res
