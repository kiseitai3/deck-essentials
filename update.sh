#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

pushd /home/deck/

./.deck-essentials/uninstall.sh

git clone 

mv deck-essentials .deck-essentials

./.deck-essentials/install.sh

popd
