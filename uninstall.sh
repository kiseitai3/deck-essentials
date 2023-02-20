#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

systemctl daemon-reload
systemctl stop deck-essentials.service
systemctl disable deck-essentials.service
systemctl daemon-reload

rm /etc/systemd/system/deck-essentials.service

pushd $HOME/
rm -r .deck-essentials

popd
