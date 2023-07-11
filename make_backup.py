import os
import typing
from datetime import date

import argparse
from pathlib import Path

import subprocess

PathLike = typing.Union[str, bytes, Path]


# try:
#     os.remove('./tmp/git-cid')
# except FileNotFoundError:
#     pass
# subprocess.run(['sudo', 'docker', 'run', '-it', '--rm', '--volume=/home/paul/webasupport/dockers/builder/dockers/allsports.new/allsports.new.allsports.new.sails:/git', '--volume=/home/paul/:/root/', '--cidfile=./tmp/git-cid', 'alpine/git', 'clone', 'http://paulweijtens@webastart.synology.me:7990/scm/p_0317_as/frontend.git', '--single-branch', '--depth', '1', '--branch', 'production', 'javascript'])
# exit()


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
    parser = argparse.ArgumentParser(
        description='Create backup of postgresql database. This is thin wrapper around pg_dump\n\nIt is important that this command is ran as root!')
    parser.add_argument('docker', help="Docker where postgresql database is contained")
    parser.add_argument('dbname', help="Database name that is copied")
    parser.add_argument('directory', help="directory where backups are contained")
    parser.add_argument('-U', '--superuser', help="Username for root access inside to postgres db")

    parsed = parser.parse_args()
    return parsed


def make_backup(docker: str, db: str, directory: str, user: str = None):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    datestr = date.today().strftime('%d-%m-%Y')
    base_fname = f'{db}-{datestr}'
    fullpath = path / f'{base_fname}.dump'
    i = 0
    while fullpath.exists():
        i += 1
        fullpath = path / f'{base_fname}.{i}.dump'

    cmd: typing.List[str] = ['sudo', 'docker', 'exec', docker, 'pg_dump', db, '-c', '-Fc', '-Z9']
    if user is not None:
        cmd.extend(['-U', user])
    success = False
    with open(fullpath, 'w') as f:
        completed_proc = subprocess.run(cmd, stdout=f)
        if completed_proc.returncode == 0:
            success = True
    if not success:
        print("no success")
        try:
            fullpath.unlink()
        except FileNotFoundError as e:
            pass


def main():
    args = parse_input()
    make_backup(args.docker, args.dbname, args.directory, args.superuser)

    return


if __name__ == "__main__":
    main()
