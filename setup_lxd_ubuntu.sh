#!/usr/bin/env bash
# install LXD
sudo add-apt-repository -y ppa:ubuntu-lxc/stable
sudo apt update
sudo apt-get install -y lxc lxd
# create storage pool
sudo lxc storage create pool1 dir
# create profile
sudo lxc profile copy default piper-ci
sudo lxc profile set piper-ci security.privileged true
sudo lxc profile device add piper-ci eth0 nic nictype=bridged parent=lxcbr0 name=eth0
sudo lxc profile device add piper-ci root disk pool=pool1 path=/
sudo lxc profile show piper-ci
# copy image
sudo lxc image copy images:alpine/3.5 local: --copy-aliases
sudo lxc image list
# setup LXD
sudo lxc config set core.https_address [::]
openssl genrsa 2048 > client.key
openssl req -new -x509 -nodes -sha1 -days 365 -key client.key -out client.crt -subj "/C=CZ/ST=Czech Republic/L=Prague/O=TEST/OU=IT Department/CN=ssl.raymii.org"
sudo lxc config trust add client.crt
mkdir ~/.config/lxc-client
mv client.* ~/.config/lxc-client/.