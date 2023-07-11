import re
import typing
from pathlib import Path

from ServerData import ServerData


def build_nginx_configuration(base_dir: Path,
                              portal_docker_fullname: str,
                              portal_fname: str,
                              servlist: typing.List[ServerData],
                              overwrite: bool = False,
                              quiet: bool = False):
    location = base_dir / portal_docker_fullname
    in_fname = location / 'sites-available' / portal_fname
    out_fname = location / 'sites-enabled' / portal_fname
    with open(in_fname.as_posix(), "r") as f:
        contents = f.readlines()

    index = find_location_line(contents)

    insert = [generate_location_string(s) for s in servlist]

    contents[index:index] = insert

    try:
        (location / 'sites-enabled').mkdir(parents=True)
    except FileExistsError:
        pass
    with open(out_fname.as_posix(), "w+") as f:
        content_str = "".join(contents)
        f.write(content_str)


def find_location_line(contents: typing.List[str]):
    # Find the line that contains `location \ ` block
    # which should be the generic redirect for anything to redirect to the SPA static code
    # If no location is found, find the first line containing a server block, and place it directly after this
    pattern = re.compile(r"^\s*location\s+/\s+\{")
    try:
        i = next(i for i, v in enumerate(contents) if pattern.match(v) is not None)
    except StopIteration:
        pattern = re.compile(r"^\s*server\s+\{")
        try:
            i = next(i for i, v in enumerate(contents) if pattern.match(v) is not None) + 1
        except StopIteration:
            return 1
    return i


def generate_location_string(server: ServerData):
    return "\tlocation {server.path} {{\n" \
           "\t\tset $upstream http://{server.name}:{server.port};\n" \
           "\t\trewrite ^{server.path}/(.*) /$1  break;\n" \
           "\t\tproxy_pass $upstream;\n" \
           "\t}}\n".format(server=server)
