#! /bin/bash

gpu=false
rebuild=true
# port should be unique for every user
uniq_port='17957'
container_name="tf_sensor_cpu"
project_name='tf_sensor_cpu'

# in home directory shoud exist
# .ssh
# .aws
# .gitconfig

image_name='korbash/minimal_notebook'
project_dir="projects"

dir="${project_dir}/${project_name}"
if ! [ -d ~/${dir} ]; then
    old=${PWD}
    cd ~/${project_dir}
    mkdir ${project_name}
    cd ${old}
fi
if ! [ -d ~/${dir}/.ssh ]; then
    cp -r ~/.ssh ~/${dir}/.ssh
fi
if ! [ -d ~/${dir}/.aws ]; then
    cp -r ~/.aws ~/${dir}/.aws
fi
if ! [ -d ~/${dir}/.gitconfig ]; then
    cp ~/.gitconfig ~/${dir}/.gitconfig
fi

if ${gpu}; then
    if ${rebuild}; then
        docker build -t ${image_name} --build-arg ROOT_CONTAINER=ubuntu:focal .
    else
        image_name='korbash/minimal_notebook_gpu'
        docker pull ${image_name}
    fi
else
    if ${rebuild}; then
        docker build -t ${image_name} --build-arg ROOT_CONTAINER=nvidia/cuda:11.2.2-runtime-ubuntu20.04 .
    else
        image_name='korbash/minimal_notebook'
        docker pull ${image_name}
    fi
fi
docker run  --name "${container_name}" --user root -e GRANT_SUDO=yes \
 -p "${uniq_port}:8888" \
 -v ~/${dir}:/home/jovyan \
 "${image_name}"
