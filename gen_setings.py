from ensurepip import version
from pprint import pprint
from re import U
import pydocker
from sacred import Experiment
import subprocess
from io import StringIO
import logging as log
import yaml
from os.path import join as jn
from pathlib import Path
from shutil import copy2, copytree, rmtree
import os

ex = Experiment()


@ex.named_config
def base():
    ssh = {'install': False}
    conda = {'install': False}
    github = {'install': False}
    version = '3.3'
    user = {
        'name': 'robot',
        'UID': 1000,
        'GID': 100,
        'sudo': True,
        'password': 'robot',
        'time_zone': 'Europe/Moscow'
    }
    user['home'] = Path('/home') / user['name']
    image = {
        'source': 'korbash',
        'name': 'simpl',
        'tag': '0.1',
        'base': 'ubuntu:18.04',
        'cont_name': None
    }
    var = {}
    packages = ['git', 'build-essential', 'nano']
    sec = ['.ssh', '.aws', '.gitconfig']
    project = {'rewrite': True, 'del_exist_pr': False}
    start_compose = {'install': True, 'reinstall': True}
    use_gpu = True


@ex.named_config
def ssh():
    ssh = {'install': True, 'port_in': 22, 'port_out': 23}


@ex.named_config
def conda(user):
    conda = {'install': True, 'base': True, 'version': 'latest', 'path': user['home'] / 'miniconda'}


@ex.named_config
def github():
    '''
    it should content item 'repo' but it added later in function specify project (isaac or sensor) 
    connect can be 'ssh' or 'http' show how we wont conect to github
    how show install dep if key 'pip_env' exist used pip, if 'conda_env' use conda, if both fierst conda second pip
    '''
    github = {
        'install': True,
        'how': {
    # 'conda_env': 'conda.yml',
    # 'pip_env': 'requirements.txt'
        },
        'connect': 'ssh',
        'githost': 'RQC-Robotics'
    }


@ex.named_config
def sensor(use_gpu):
    if use_gpu:
        image = {
            'base': 'nvidia/cuda:11.2.1-cudnn8-runtime-ubuntu20.04',
            'name': 'sensor_gpu'
        }
    else:
        image = {'base': 'ubuntu:18.04', 'name': 'sensor_cpu'}
    github = {'repo': 'RQC-Robotics-tactile_sensor'}


@ex.named_config
def isaac(use_gpu, packages, conda, user):
    if not use_gpu:
        log.error('isaac gym mast have GPU axes')
        exit()
    var = {'LD_LIBRARY_PATH': [str(conda['path']) + '/envs/rlgpu/lib',
    str(user['home']) + '/src/isaacgym/python/isaacgym/_bindings/linux-x86_64/']} # if use isaac with defalt conda env 
    packages += ['libxcursor-dev', 'libxrandr-dev', 'libxinerama-dev', 'libxi-dev',
    'mesa-common-dev', 'zip', 'unzip', 'make', 'gcc-8', 'g++-8', 'vulkan-utils',
    'mesa-vulkan-drivers', 'pigz', 'git', 'libegl1', 'git-lfs']
    # sec += ['src/isaacgym']
    version = '2.3'
    image = {
        'base': 'nvidia/cuda:10.2-runtime-ubuntu18.04',
        'name': 'isaacgym'
    }
    github = {'repo': 'isaacGym'}


@ex.named_config
def post_cfg(image):
    project = {'name': image['name']}
    image['full_name'] = f"{image['source']}/{image['name']}:{image['tag']}"
    host_name = image['name']


def gen_bash(dict):
    st = ''
    it = iter(dict.items())
    comand, arg = next(it)
    for name, val in it:
        st += str(name) + ' ' + str(val) + ' '
    st = str(comand) + ' ' + st + ' ' + str(arg)
    return st


@ex.capture
def create_project_dir(d, project, sec, user):
    name = project['name']
    hm = Path.home()
    pr = hm / 'projects' / name
    try:
        pr.mkdir(parents=True)
    except:
        if project['del_exist_pr']:
            rmtree(pr)
            log.info('delited progect dir with the same name')
            pr.mkdir()
        else:
            log.warn('project %s alredy exist' % name)
    for f in sec:

        src = hm / f
        dest = pr / f
        try:
            if src.is_file():
                if dest.exists() and project['rewrite']:
                    dest.unlink()
                if not dest.exists():
                    copy2(src, dest)
            else:
                if dest.exists() and project['rewrite']:
                    rmtree(dest)
                if not dest.exists():
                    copytree(src, dest)
            # d.COPY = f + ' ' + str(user['home'] / f)
        except FileNotFoundError as exc:
            log.error(f'{exc}\nso file has skipped')
    os.chdir(str(pr))
    return pr


@ex.capture(prefix='user')
def add_user(d, name, password, UID, GID, sudo, home, time_zone):
    d.ENV = 'TZ=' + time_zone + ' DEBIAN_FRONTEND=noninteractive'
    d.RUN = 'ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone'
    d.RUN = gen_bash({
        'adduser': name,
        '--disabled-password': '',
        '--uid': UID,
        '--gid': GID,
        '--home': str(home)
    })
    d.RUN = "echo '%s:%s' | chpasswd" % (name, password)
    if sudo:
        d.RUN = "apt update && apt install -y sudo"
        d.RUN = "echo '%s ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers" % name
    d.USER = name
    d.WORKDIR = str(home / 'project')
    d.COPY = '. ' + str(home)
    d.RUN = 'sudo chown -R robot ~/'


@ex.capture
def install_pac_var(d, packages, var):
    d.RUN = 'sudo apt update && sudo apt install -y ' + ' '.join(
        map(str, packages))
    st = '\n'.join(map(lambda x: 'export %s=%s' % (x,':'.join(var[x])), var))
    d.RUN = "echo '%s' >> ~/.profile" % st


@ex.capture(prefix='ssh')
def install_ssh(d, port_in):
    d.RUN = 'sudo apt update && sudo apt install -y openssh-server'
    d.RUN = 'sudo service ssh start'
    d.EXPOSE = port_in
    d.ENTRYPOINT = ['sudo', '/usr/sbin/sshd', '-D']


@ex.capture(prefix='conda')
def install_conda(d, version, base, path):
    d.RUN = 'wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-' + version + '-Linux-x86_64.sh -O ~/miniconda.sh'
    d.RUN = 'chmod +x ~/miniconda.sh && ~/miniconda.sh -b -p %s && rm ~/miniconda.sh' % str(path)
    d.RUN = "echo '. %s/etc/profile.d/conda.sh' >> ~/.profile" % str(path)
    if base:
        d.RUN = '. ~/.profile && conda init bash'


@ex.capture()
def clone_instal_repo(d, github, conda):
    repo = github['repo']
    githost = github['githost']
    how = github['how']
    # if conda['install']:
    #     how = {}
    #     for key in github['how']:
    #         how[key] = '~/.profile && conda activate ' + github['how'][key]
    if github['connect'] == 'ssh':
        d.RUN = 'git clone git@github.com:' + githost + '/' + repo + '.git'
    elif github['connect'] == 'http':
        d.RUN = 'git clone https://github.com/:' + githost + '/' + repo + '.git'
    else:
        log.error(
            'fail clone repo,connect= %s unsuported, shoud be ssh or http')
        return
    d.WORKDIR = repo
    b = '. ~/.profile && conda activate && ' if conda['install'] else ''
    comand = lambda a, b: "if [ -f '{a}' ] ; then {b} {a} ; else echo '{a} not found' ; fi".format(
        a=a, b=b)
    if 'conda_env' in how and conda['install']:
        d.RUN = comand(how['conda_env'], b + 'conda create -f')
    if 'pip_env' in how:
        d.RUN = comand(how['pip_env'], b + 'pip install -r')


@ex.capture()
def create_docker_compose_yaml(ports, image, use_gpu, user, host_name, version):
    hp = Path('.')
    cp = Path(user['home'])
    volumes = []
    for cld in hp.iterdir():
        volumes += ['./%s:%s' % (cld, cp.joinpath(cld.name))]
    my_name = 'docker-compose.yaml'
    if not (hp / my_name).exists():
        volumes += ['./%s:%s' % (hp / my_name, cp / my_name)]
    log.debug('volums: ' + str(volumes))
    build = {
        'build': {
            'context': '.'    # 'dockerfile': 'Dockerfile.' + image['name']
        },
        'hostname': host_name,
        'volumes': volumes,
        'tty': True,
        'stdin_open': True
    }
    if image['cont_name'] is not None:
        build['container_name'] = image['cont_name']
    if len(ports) > 0:
        build['ports'] = [
            '%s:%s' % (p_out, p_in) for p_out, p_in in ports.items()
        ]
    if use_gpu:
        build['runtime'] = 'nvidia'

    compose = {'version': version, 'services': {image['name']: build}}
    with open('docker-compose.yaml', 'w') as f:
        yaml.dump(compose, f)


@ex.capture
def start_docker_compose(start_compose):
    out = subprocess.run(['docker-compose', 'ps', '-q'],
                         capture_output=True,
                         text=True).stdout
    if out != '' and start_compose['reinstall']:
        log.info('remove exsisted compose service')
        subprocess.run(['docker-compose', 'down'])
    elif out != '':
        log.error('compose service alredy build')
        return
    subprocess.run(['docker-compose', 'up', '-d', '--build'])


@ex.automain
def my_main(image, ssh, conda, github, start_compose):
    ports = {}
    d = pydocker.DockerFile(base_img=image['base'], name=image['full_name'])
    add_user(d)
    create_project_dir(d)
    install_pac_var(d)
    if ssh['install']:
        install_ssh(d)
        ports[ssh['port_out']] = ssh['port_in']
    if conda['install']:
        install_conda(d)
    if github['install']:
        clone_instal_repo(d)
    d.generate_files(dockefile_name='Dockerfile')
    create_docker_compose_yaml(ports)
    if start_compose['install']:
        start_docker_compose()
