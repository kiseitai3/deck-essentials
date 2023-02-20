#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

pushd /home/deck/

./.deck-essentials/uninstall.sh

git clone https://github.com/kiseitai3/deck-essentials.git

mv deck-essentials .deck-essentials

chmod +x ./.deck-essentials/*.sh

./.deck-essentials/install.sh

popd
