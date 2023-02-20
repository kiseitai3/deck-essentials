#!/bin/bash
if [[ $(id -u) != 0 ]]; then
  pkexec "$0"
  exit 0
fi

pre-install () {
  case $1 in
    nfs-utils)
      mv -f /etc/request-key.d/id_resolver.conf /etc/request-key.d/id_resolver.conf.bak
      rm -r /var/lib/nfs/
    ;;
  esac
}

install_util () {
  pacman -S "$1" --noconfirm --needed
}

uninstall_util () {
  pacman -R "$1"
}


install_config () {
  case $1 in
    bluetooth-mic-config)
      TARGET=""
      if [ -f "$TARGET" ] && [ ! -f "$TARGET.bak" ]; then
        mv -f "$TARGET" "$TARGET.bak"
      fi
      cp "$1" "$TARGET"
    ;;
    aggregate-nic-config)
      python3 deck-essentials-aggregate-nics.py down
      python3 deck-essentials-aggregate-nics.py up
    ;;
  esac
}

uninstall_config () {
  case $1 in
    bluetooth-mic-config)
      TARGET=""
      if [ -f "$TARGET.bak" ]; then
        mv -f "$TARGET.bak" "$TARGET"
      else
        rm "$TARGET"
      fi
    ;;
    aggregate-nic-config)
      python3 deck-essentials-aggregate-nics.py down
    ;;
  esac
}

post-install () {
  case $1 in
    networkmanager-openvpn)
      systemctl restart NetworkManager
    ;;
  esac
}

mkdir -p $HOME/.deck-essentials >/dev/null 2>&1
pushd $HOME/.deck-essentials

cp /etc/os-release os-update

if [ ! -f "os" ]; then
  touch os
fi

if [[ "$(< os-update)" != "$(< os)" ]]; then
  echo "Installing" > status.txt
  notify-send "System Upgraded" "Reinstalling missing sys-essentials packages!"
  
  systemd-sysext unmerge

  steamos-readonly disable

  pacman-key --init
  pacman-key --populate

  pacman -Syy

  while read -r line
    do
      pre-install "$line"
      install_util "$line"
      post-install "$line"
  done < utils.txt

  while read -r line
    do
      install_config "$line"
  done < configs.txt

  while read -r line
    do
      uninstall_util "$line"
  done < remove_utils.txt
  echo "" > remove_utils.txt

  while read -r line
    do
      uninstall_config "$line"
  done < remove_configs.txt
  echo "" > remove_configs.txt

  steamos-readonly enable

  cp os-update os
  
  systemd-sysext refresh

  echo "Restart" > status.txt
  notify-send "System Upgraded" "deck-essentials completed! You may need to restart the system for changes to take effects."

else

  echo "Installed" > status.txt

fi

popd
