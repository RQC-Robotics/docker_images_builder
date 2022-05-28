#! /bin/bash

gpu=true
rebuild=true
# port should be unique for every user
uniq_port='17957'
container_name="tf_sensor_gpu3"
project_name='tf_sensor_gpu2'
key_dir='projects'
# in home directory shoud exist
# .ssh
# .aws
# .gitconfig

image_name='korbash/minimal_notebook_gpu:0.1'
project_dir="projects"

dir="${project_dir}/${project_name}"
if ! [ -d ~/${dir} ]; then
    old=${PWD}
    cd ~/${project_dir}
    mkdir ${project_name}
    cd ${old}
fi
if ! [ -d ~/${dir}/.ssh ]; then
    cp -r ~/${key_dir}/.ssh ~/${dir}/.ssh
fi
if ! [ -d ~/${dir}/.aws ]; then
    cp -r ~/${key_dir}/.aws ~/${dir}/.aws
fi
if ! [ -d ~/${dir}/.gitconfig ]; then
    cp ~/${key_dir}/.gitconfig ~/${dir}/.gitconfig
fi

if ${gpu}; then
    if ${rebuild}; then
        docker build -t ${image_name} --build-arg ROOT_CONTAINER=tensorflow/tensorflow:latest-gpu .
    else
        image_name='korbash/minimal_notebook_gpu'
        docker pull ${image_name}
    fi
    docker run  --name "${container_name}" --user root -e GRANT_SUDO=yes \
     --gpus all \
     -p "${uniq_port}:8888" -p 17956:6006 \
     -v ~/${dir}:/home/jovyan \
     "${image_name}"

else
    if ${rebuild}; then
        docker build -t ${image_name} --build-arg ROOT_CONTAINER=ubuntu:focal .
    else
        image_name='korbash/minimal_notebook'
        docker pull ${image_name}
    fi
    docker run  --name "${container_name}" --user root -e GRANT_SUDO=yes \
     -p "${uniq_port}:8888" \
     -v ~/${dir}:/home/jovyan \
     "${image_name}"
fi
