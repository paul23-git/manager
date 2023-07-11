import os
import re
import shutil
from pathlib import Path

from util import test_location


def make_node_dockerfile(base_dir: Path,
                         name: str,
                         node_version: str = '12',
                         overwrite: bool = False,
                         no_overwrite: bool = False,
                         quiet: bool = False) -> Path:
    location = base_dir / name / 'Dockerfile'
    if test_location(location, overwrite, quiet or no_overwrite):
        os.remove(location.as_posix())
    with open('node-template/Dockerfile-nodejs', 'r') as infile, open(location.as_posix(), 'w+') as outfile:
        for line in infile:
            outfile.write(convert_dockerfile_command(line, node_version))
    return base_dir / name


def convert_dockerfile_command(line: str, nodeversion: str) -> str:
    if re.match(r"^\s*FROM\s+node:", line, re.IGNORECASE):
        return 'FROM node:{nodeversion}-alpine\n'.format(nodeversion=nodeversion)
    return line


def make_nginx_dockerfile(base_dir: Path,
                          name: str,
                          nginx_version: str = '1.7.18',
                          overwrite: bool = False,
                          no_overwrite: bool = False,
                          quiet: bool = False) -> Path:
    nginx_dir = base_dir / name
    if test_location(nginx_dir, overwrite, quiet or no_overwrite):
        shutil.rmtree(nginx_dir)
    shutil.copytree('nginx-template', nginx_dir.as_posix())
    return nginx_dir


def make_redis_dockerfile(base_dir: Path,
                          name: str,
                          redis_version: str = '1.7.18',
                          overwrite: bool = False,
                          no_overwrite: bool = False,
                          quiet: bool = False) -> Path:
    redis_dir = base_dir / name
    if test_location(redis_dir, overwrite, quiet or no_overwrite):
        shutil.rmtree(redis_dir)
    shutil.copytree('redis-template', redis_dir.as_posix())
    return redis_dir
