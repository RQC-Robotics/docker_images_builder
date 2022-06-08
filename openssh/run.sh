#! bin/bash

docker run -p 23:22 -d --gpus=all --ipc=host --name isaac korbash/isaacgym:0.0
