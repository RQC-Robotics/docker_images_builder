FROM korbash/isaacgym:base

USER root

RUN apt update

RUN apt install  openssh-server sudo -y
 
RUN service ssh start

RUN  echo 'gymuser:trifinger007' | chpasswd

EXPOSE 22

CMD ["/usr/sbin/sshd","-D"]
