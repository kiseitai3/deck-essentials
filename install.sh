#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

pushd /home/deck/
#git clone
#rm -r .sys-essentials
#mv sys-essentials .sys-essentials
cd .sys-essentials
./sys-essentials.sh
cp ./sys-essentials.service /etc/systemd/system/sys-essentials.service

systemctl daemon-reload
systemctl enable sys-essentials.service --now

chown -R root:root ./
chmod -R 755 ./

popd
