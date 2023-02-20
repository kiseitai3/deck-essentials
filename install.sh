#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

pushd $HOME/
cd .deck-essentials
cp ./deck-essentials.service /etc/systemd/system/deck-essentials.service

systemctl daemon-reload
systemctl enable deck-essentials.service --now

chown -R root:root ./
chmod -R 755 ./
chmod -R 666 *.txt
chmod 666 os*

popd
