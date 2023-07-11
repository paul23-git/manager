import itertools
import shutil
import subprocess
from pathlib import Path
from typing import Sequence, Optional

from DockerService import DockerService
from git_util import load_git, update_git, get_current_branch_name, get_latest_tag, get_current_full_commit_sha
from DockerCompose import DockerCompose


def update(compose: DockerCompose,
           base_dir: Path,
           name: str,
           branch: Optional[str],
           git_settings: Sequence[str],
           build_env=None,
           quiet: bool = False):
    # updates a container in the network
    # branch can be anything from a branch, a tag or a git SHA code
    # Without branch the behaviour is based on previously given branch:
    # if previous was a branch it will be the latest commit to that branch
    # if previous was a tag/sha it will be that specific tag/sha
    basename = base_dir.parts[-1]
    fullname = '{basename}.{name}'.format(basename=basename, name=name)
    location = base_dir / fullname / 'javascript'

    if not quiet:
        print('loading from git....')
    update_git(base_dir, fullname, branch, git_settings, quiet)

    actual_branch = get_current_branch_name(base_dir, fullname)
    latest_tag = get_latest_tag(base_dir, fullname)
    commit = get_current_full_commit_sha(base_dir, fullname)

    if build_env is not None:
        compose.meta.clear_build_environment(fullname)
        for env in build_env:
            k, v = env.split('=', 1)
            compose.meta.set_build_environment_variable(fullname, k, v)

    if not quiet:
        print("Transpiling javascript....")
    scr = compose.meta.get_compile_script(fullname)
    environment = compose.meta.get_build_environment(fullname)

    if scr is not None:
        scr(location, environment)

    dckr = compose.get_docker(fullname)  # type: Optional[DockerService]
    if dckr is not None:
        if commit is not None:
            dckr.set_environment_variable('GIT_COMMIT', commit)
        if actual_branch is not None:
            dckr.set_environment_variable('GIT_BRANCH', actual_branch)
        if latest_tag is not None:
            dckr.set_environment_variable('GIT_LATEST_TAG', latest_tag)

    return [dckr]

