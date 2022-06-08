#! bin/bash

docker run -p 23:22 -d --gpus=all --ipc=host --name isaac \
 -v ~/.ssh:/home/gymuser/.ssh \
 -v ~/.aws:/home/gymuser/.aws \
 -v ~/.gitconfig:/home/gymuser/.gitconfig \
 korbash/isaacgym:0.0
