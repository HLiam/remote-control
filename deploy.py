# to use this, you must have a `.env` file that contains a `KEY` environment variable

import os
from contextlib import suppress, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from shutil import copy
from subprocess import Popen, call, PIPE
from sys import argv, exit


@dataclass
class DeployFile:
    """A file that has a source (copy from) and a destination (copy to)."""

    def __init__(self, src: Path, dest: Path):
        self.src = Path(src)
        self.dest = Path(dest)

    def deploy(self):
        with suppress(FileNotFoundError):
            self.dest.unlink()
        with suppress(FileNotFoundError):
            copy(self.src, self.dest)


# TODO:
# - make this deploy script work when called from any location
# - clean these up
cur_location = Path(__file__).parent.absolute()
name = 'remote_control'
dest = Path('~/AppData/Local', name).expanduser()
startup_dir = Path(
    '~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup').expanduser()

symlink_path = startup_dir/name
exe_name = f'{name}.exe'
exe_file = DeployFile(Path(cur_location, 'target/release', exe_name), dest/exe_name)
dot_env_file = DeployFile(cur_location/'.env', dest/'.env')
rocket_config_file = DeployFile(cur_location/'Rocket.toml', dest/'Rocket.toml')
files_to_deploy = [exe_file, rocket_config_file, dot_env_file]


class ProccessKillError(Exception):
    pass


def print_usage():
    print('\n'.join(('This script will start start the program as well as add it to the startup directory',
                     '\n\nusage: py deploy_win.py [options]',
                     '\noptions:',
                     '    -h, --help    Show this help information.',
                    f'    -k, --kill    Kill the {name} process currently running (if there is one) then exit.')))


def exit_with_err(msg: str, end='\n'):
    print(f'Error: {msg}', end)
    exit()


def kill_proccess(name: str):
    with StringIO() as buf, redirect_stdout(buf):
        p = Popen(['taskkill', '/f', '/im', name], stdout=PIPE, stderr=PIPE)
        err_msg = p.stderr.read()
        if err_msg:
            raise ProccessKillError(str(buf))


def build():
    call(['cargo', 'build', '--release', '--manifest-path', str(cur_location/'Cargo.toml')])


def handle_invalid_config():
    if os.getenv('KEY') is None and 'KEY' not in dot_env_file.src.read_text():
        exit_with_err('no environment variable set or presence in `.env` for `KEY`')
    if not rocket_config_file.src.exists():
        exit_with_err('no `Rocket.toml` present')


def main():
    handle_invalid_config()
    success_msg = f'Process {exe_name} started'

    with suppress(IndexError):
        if argv[1] in ('-h', '--help'):
            print_usage()
            return
        if argv[1] in ('-k', '--kill'):
            with suppress(ProccessKillError):
                kill_proccess(exe_name)
            return

    with suppress(FileExistsError):
        dest.mkdir()
    build()

    with suppress(ProccessKillError):
        kill_proccess(exe_name)
        success_msg += ' & old process was killed'

    for deploy_file in files_to_deploy:
        deploy_file.deploy()

    with suppress(FileNotFoundError):
        symlink_path.unlink()
    symlink_path.symlink_to(exe_file.dest)
    os.startfile(exe_file.dest)

    print(success_msg)


if __name__ == '__main__':
    main()
