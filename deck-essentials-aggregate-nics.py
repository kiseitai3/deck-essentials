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
  ret = subprocess.check_output('ls /sys/class/net', shell=True).decode().strip().split('\n')

  #Filter the interface list by wireless or ethernet. We don't want anything else.
  available_if = [i for i in ret if 'wl' in i.lower() or 'en' in i.lower()]

  #Now,let's register the aggregate interface. We want balance-alb to squeeze as much throughput 
  #in docked mode while preserving fault tolerance (aka undocking and losing the ethernet interface)
  subprocess.call('nmcli connection add type bond con-name bond0 ifname bond0 bond.options "mode=balance-alb,miimon=1000"', shell=True)

  #Now, we iterate through every interface available to us and bind them to our aggregate bond.
  #If we get this correctly, we can dock and undock while preserving at least one link for gaming over NFS.
  #Of course, be ware of issues due to loss of bandwidth due to going from 2 interfaces to 1 and the latency
  #penalty due to the loss of the ethernet interface when undocked.
  #Some latency may be introduced when some of the traffic is routed throught the wireless interface, but this is currently experimental.
  port = 1
  for interface in available_if:
    if 'en' in interface:
      subprocess.call('nmcli connection add type ethernet slave-type bond con-name bond0-port{} ifname {} master bond0'.format(port, interface),shell=True)
    else:
      subprocess.call('nmcli connection add type wifi slave-type bond con-name bond0-port{} ifname {} master bond0'.format(port, interface),shell=True)
    port += 1
    
  #Now, let's activate the interface
  subprocess.call('nmcli connection up bond0', shell=True)
  subprocess.call('nmcli connection modify bond0 connection.autoconnect-slaves 1', shell=True)
  subprocess.call('nmcli connection up bond0', shell=True)
    
def deaggregate():
  #Stop the connection
  subprocess.call('nmcli connection down bond0', shell=True)
  #Remove the connection
  subprocess.call('nmcli connection delete bond0', shell=True)
  
if len(argv) > 1:
  if argv[1] == 'up':
    aggregate()
  elif argv[1] == 'down':
    deaggregate() 
  
  
  
  
