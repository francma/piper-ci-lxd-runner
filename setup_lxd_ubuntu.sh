#!/usr/bin/env bash
# setup LXD group
sudo groupadd --system lxd
sudo usermod -a -G lxd $USER
# install lxd
sudo apt-get --yes install snapd
sudo snap install lxd
# create profile
sudo lxd waitready
printf 'y\ndefault\ndir\ny\nall\n8443\ny\ny\nlxdbr0\nauto\nauto\n' | sudo lxd init
sudo lxd.lxc profile copy default piper-ci
sudo lxd.lxc profile set piper-ci security.privileged true
# copy image
sudo lxd.lxc image copy images:alpine/3.5 local: --copy-aliases
# setup LXD
openssl genrsa 2048 > client.key
openssl req -new -x509 -nodes -sha1 -days 365 -key client.key -out client.crt -subj "/C=CZ/ST=Czech Republic/L=Prague/O=TEST/OU=IT Department/CN=ssl.raymii.org"
sudo lxd.lxc config trust add client.crt
mkdir ~/.config/lxc-client
mv client.* ~/.config/lxc-client/.