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
  
  #Fetch the existing wifi profiles. We need to bind the ssids later to the wifi slave so we can seemlessly connect between known wifi connections.
  #It should still fail if moving the deck to a new network, but we can always rerun this script to regenerate a new bond profile.
  ret = subprocess.check_output('nmcli connection show | grep wifi', shell=True).decode().strip().split('\n')
  
  #Filter the garbage out of the returned data
  wifi_profiles = []
  for r in ret:
    line = r.split('  ')
    line = [cell.strip() for cell in line if len(cell)]
    wifi_profiles.append(line)
  
  #Now, get all of the ethernet connections like we did for the wifi
  ret = subprocess.check_output('nmcli connection show | grep ethernet', shell=True).decode().strip().split('\n')
  eth_profiles = []
  for r in ret:
    line = r.split(' ')
    line = [cell for cell in line if len(cell)]
    eth_profiles.append(line)
    
  #Let's make sure these connections are turned off and set to never autoconnect. If all goes well, we will autoconnect via the bond interface
  profiles = wifi_profiles + eth_profiles
  for profile in profiles:
    subprocess.call('nmcli connection down {}'.format(profile[0]),shell=True)
    subprocess.call('nmcli connection modify {} autoconnect no'.format(profile[0]),shell=True)

  #Now,let's register the aggregate interface. We want balance-alb to squeeze as much throughput 
  #in docked mode while preserving fault tolerance (aka undocking and losing the ethernet interface)
  subprocess.call('nmcli connection add type bond con-name bond0 ifname bond0 bond.options "mode=balance-alb,fail_over_mac=active,miimon=100,primary_reselect=always,updelay=200"', shell=True)

  #Now, we iterate through every interface available to us and bind them to our aggregate bond.
  #If we get this correctly, we can dock and undock while preserving at least one link for gaming over NFS.
  #Of course, be ware of issues due to loss of bandwidth due to going from 2 interfaces to 1 and the latency
  #penalty due to the loss of the ethernet interface when undocked.
  #Some latency may be introduced when some of the traffic is routed throught the wireless interface, but this is currently experimental.
  port = 1
  primary_interface = ""
  for interface in available_if:
    if interface.startswith('en'):
      cmd = 'nmcli connection add type ethernet slave-type bond con-name bond0-port{} ifname {} master bond0'.format(port, interface)
      print(cmd)
      subprocess.call(cmd,shell=True)
      subprocess.call('nmcli connection up bond0-port{}'.format(port),shell=True)
      primary_interface = interface
    else:
      wifi_port = 1
      for profile in wifi_profiles:
        password = subprocess.check_output('nmcli --show-secrets connection show "{}" | grep 802-11-wireless-security.psk:'.format(profile[0]),shell=True).decode().strip().split(':')[-1].strip()
        cmd = 'nmcli connection add type wifi slave-type bond con-name bond0-port{}-wifi{} ifname {} master bond0 ssid {} con-name bond0-port{}-wifi{}'.format(port, wifi_port, interface, profile[0], port, wifi_port)
        print(cmd)
        subprocess.call(cmd,shell=True)
        try:
          subprocess.call('nmcli connection modify bond0-port{}-wifi{} wifi-sec.key-mgmt wpa-psk wifi-sec.psk "{}"'.format(port, wifi_port, password),shell=True)
          subprocess.call('nmcli connection up bond0-port{}-wifi{}'.format(port, wifi_port),shell=True)
        except:
          subprocess.call('nmcli connection delete bond0-port{}-wifi{}'.format(port, wifi_port))
        wifi_port += 1
    port += 1
    
  #let's copy the mac policy so the bond can work properly.
  #Courtesy of https://github.com/coreos/fedora-coreos-tracker/issues/919
  subprocess.call('cp 98-bond-inherit-mac.link /etc/systemd/network/98-bond-inherit-mac.link', shell=True)
  subprocess.call('systemctl daemon-reload', shell=True)
  
  #Now, let's activate the interface and set a few final options
  #subprocess.call('nmcli connection up bond0', shell=True)
  #print('nmcli connection modify bond0 +bond.options "primary={}"'.format(primary_interface))
  #subprocess.call('nmcli connection modify bond0 +bond.options "primary={}"'.format(primary_interface), shell=True)
  subprocess.call('nmcli connection modify bond0 connection.autoconnect-slaves 1', shell=True)
  subprocess.call('nmcli connection up bond0', shell=True)
      
    
def deaggregate():
  #We first need to list all bond connections and delete them in reverse order (ports first then the master
  ret = subprocess.check_output('nmcli connection show | grep bond0', shell=True).decode().strip().split('\n')
  connections = ret[::-1]
  for connection in connections:
    connection_name = connection.split(' ')[0]
    #Stop the connection
    subprocess.call('nmcli connection down {}'.format(connection_name), shell=True)
    #Remove the connection
    subprocess.call('nmcli connection delete {}'.format(connection_name), shell=True)
  
if len(argv) > 1:
  if argv[1] == 'up':
    aggregate()
  elif argv[1] == 'down':
    deaggregate() 
  
  
  
  
