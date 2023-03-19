#!/usr/bin/env python3

import subprocess
from sys import argv

#Script based on https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/configuring-network-bonding_configuring-and-managing-networking
def aggregate():
  #Let's get a list of available interfaces from the system interface.
  #Two character prefixes based on the type of interface:
  # *   en -- ethernet
  # *   sl -- serial line IP (slip)
  # *   wl -- wlan
  # *   ww -- wwan
  # *   lo -- loopback
  # *   vir -- virtual
  # *   br  --  bridge
  ret = subprocess.check_output('ls /sys/class/net', shell=True).decode().strip().split('\n')

  #Filter the interface list by wireless or ethernet. We don't want anything else.
  available_if = [i for i in ret if i.startswith('wl') or i.startswith('en')]
  
  #Gather profiles set up by network manager so we can generate static configurations later
  profiles = subprocess.check_output('ls /etc/NetworkManager/system-connections', shell=True).decode().strip().split('\n')
    
  #Let's make sure these connections are turned off and set to never autoconnect. If all goes well, we will autoconnect via the bond interface
  profiles = wifi_profiles + eth_profiles
  for profile in profiles:
    subprocess.call('nmcli connection down {}'.format(profile[0]),shell=True)
    subprocess.call('nmcli connection modify {} autoconnect no'.format(profile[0]),shell=True)

  #Now,let's register the aggregate interface. We want balance-alb to squeeze as much throughput 
  #in docked mode while preserving fault tolerance (aka undocking and losing the ethernet interface)
  subprocess.call('cp 30-bond0-deck-essentials.netdev /etc/systemd/network/30-bond0-deck-essentials.netdev', shell=True)  
  subprocess.call('cp 30-bond0-deck-essentials.network /etc/systemd/network/30-bond0-deck-essentials.network', shell=True)
  subprocess.call('cp supplicant@.service /etc/systemd/system/supplicant@.service', shell=True)
  
  #Now, we iterate through every interface available to us and bind them to our aggregate bond.
  #If we get this correctly, we can dock and undock while preserving at least one link for gaming over NFS.
  #Of course, be ware of issues due to loss of bandwidth due to going from 2 interfaces to 1 and the latency
  #penalty due to the loss of the ethernet interface when undocked.
  #Some latency may be introduced when some of the traffic is routed throught the wireless interface, but this is currently experimental.
  port = 1
  primary_interface = ""
  for interface in available_if:
    if interface.startswith('en'):
      with open('30-ethernet-bond0-deck-essentials.network', 'rt') as conf:
        with open('/etc/systemd/network/30-ethernet-bond0-deck-essentials.network', 'wt') as target:
          target.write(conf.read().format(eth=interface, primary=not bool(len(primary_interface))))
      primary_interface = interface
    else:
      wifi_connections = []
      for profile in wifi_profiles:
        try:
          password = subprocess.check_output('cat /etc/NetworkManager/system-connections/{} | grep psk='.format(profile),shell=True).decode().strip()
          if len(password):
            wifi_connections.append('network={\n\tssid="{ssid}"\n\tpsk={psk}\n}'.format(ssid=profile.replace('.nmconnection', ''), psk=password))
        except:
          pass
      
      with open('30-wifi-bond0-deck-essentials.network', 'rt') as conf:
        with open('/etc/systemd/network/30-wifi-bond0-deck-essentials.network', 'wt') as target:
          target.write(conf.read().format(wifi=interface))
      with open('wpa_supplicant.conf', 'rt') as conf:
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'wt') as target:
          target.write(conf.read().format(connections='\n'.join(wifi_connections)))
      subprocess.call('systemctl enable supplicant@{} --now'.format(interface), shell=True)
    
  #let's copy the mac policy so the bond can work properly.
  #Courtesy of https://github.com/coreos/fedora-coreos-tracker/issues/919
  subprocess.call('cp 98-bond-inherit-mac-deck-essentials.link /etc/systemd/network/98-bond-inherit-mac-deck-essentials.link', shell=True)
  
  #Now, let's activate the interface and set a few final options
  #subprocess.call('nmcli connection up bond0', shell=True)
  #print('nmcli connection modify bond0 +bond.options "primary={}"'.format(primary_interface))
  #subprocess.call('nmcli connection modify bond0 +bond.options "primary={}"'.format(primary_interface), shell=True)
  #subprocess.call('nmcli connection modify bond0 connection.autoconnect-slaves 1', shell=True)
  #subprocess.call('nmcli connection up bond0', shell=True)
  subprocess.call('systemctl enable systemd-resolved --now', shell=True)
  subprocess.call('systemctl enable systemd-networkd --now', shell=True)
  subprocess.call('systemctl daemon-reload', shell=True)
      
    
def deaggregate():
  #We first need to list all bond connections and delete them in reverse order (ports first then the master
  try:
    ret = subprocess.check_output('nmcli connection show | grep bond0', shell=True).decode().strip().split('\n')
    connections = ret[::-1]
    for connection in connections:
      connection_name = connection.split(' ')[0]
      #Stop the connection
      subprocess.call('nmcli connection down {}'.format(connection_name), shell=True)
      #Remove the connection
      subprocess.call('nmcli connection delete {}'.format(connection_name), shell=True)
  except:
    pass
  profiles = subprocess.check_output('ls /etc/NetworkManager/system-connections', shell=True).decode().strip().split('\n')
  subprocess.call('rm /etc/systemd/network/*deck-essentials.*', shell=True)
  for profile in profiles:
    try:
      subprocess.call('systemctl stop supplicant@{}'.format(profile.replace('.nmconnection', '')), shell=True)
      subprocess.call('systemctl disable supplicant@{}'.format(profile.replace('.nmconnection', '')), shell=True)
    except:
      pass
  subprocess.call('rm -f /etc/systemd/system/supplicant@.service', shell=True)
  subprocess.call('systemctl daemon-reload', shell=True)
  
if len(argv) > 1:
  if argv[1] == 'up':
    aggregate()
  elif argv[1] == 'down':
    deaggregate() 
  
  
  
  
