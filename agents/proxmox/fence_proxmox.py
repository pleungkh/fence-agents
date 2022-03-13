#!@PYTHON@ -tt

# This agent uses Proxmox VE API
# This version was inspired by the fence_pve 
# 	inside https://github.com/ClusterLabs/fence-agents/tree/main/agents/pve

import sys
import requests
import urllib3
import json

import atexit
import logging
sys.path.append("@FENCEAGENTSLIBDIR@")
from fencing import atexit_handler, all_opt, check_input, process_input, show_docs, fence_action, run_delay
from fencing import fail, fail_usage, EC_LOGIN_DENIED, EC_STATUS

#BEGIN_VERSION_GENER`ATION
RELEASE_VERSION=""
BUILD_DATE=""
REDHAT_COPYRIGHT=""
#END_VERSION_GENERATION


def get_power_status(conn, options):
	logging.info(get_power_status)
	state = {"running" : "on", "stopped" : "off"}

	baseurl='https://' + options["--ip"] + ':' + options["--ipport"]
	url=baseurl + '/api2/json/nodes/' + options["--nodename"] + '/qemu/' + options["--plug"] + '/status/current'
	session_cookies = {'PVEAuthCookie': options["--ticket"] }
	hdr={"CSRFPreventionToken" : options["--CSRFPreventionToken"] }
	r = conn.get(url,cookies=session_cookies, headers=hdr)
	if r.status_code != 200:
		r.close()
		return None    
	tdata=r.json()
	result=tdata["data"]
	r.close()
	if result["status"] in state:
		return state[result["status"]]
	else:
		return None

def set_power_status(conn, options):
	logging.info(set_power_status)
	action = {
		'on' : "start",
		'off': "stop"
	}[options["--action"]]

	baseurl='https://' + options["--ip"] + ':' + options["--ipport"]
	session_cookies = {'PVEAuthCookie': options["--ticket"] }
	url=baseurl + '/api2/json/nodes/' + options["--nodename"] + '/qemu/' + options["--plug"] + '/status/' + action

	hdr={"CSRFPreventionToken" : options["--CSRFPreventionToken"] }
	r = conn.post(url, cookies=session_cookies, headers=hdr)
	if r.status_code != 200:
		r.close()
		fail(EC_STATUS)
	else:
		r.close()


def get_outlet_list(conn, options):
	logging.info(get_outlet_list)
	baseurl='https://' + options["--ip"] + ':' + options["--ipport"]
	session_cookies = {'PVEAuthCookie': options["--ticket"] }
	outlets=dict()

	url=baseurl + '/api2/json/nodes'
	r = conn.get(url,cookies=session_cookies) 
	if r.status_code != 200:
		r.close()
		return None    
	tdata=r.json()
	result=tdata["data"]
	for nd in result:
		nodename = nd['node']
		url=baseurl + '/api2/json/nodes/'+ nodename+ '/qemu'
		r = conn.get(url,cookies=session_cookies)
		if r.status_code != 200:
			r.close()
			return None    
		tdata=r.json()
		vmlist=tdata["data"]
		for vm in vmlist:
			outlets[str(vm["vmid"])] = (vm["name"], {'running':"on",'stopped': "off"}[vm["status"]])
	r.close()
	return outlets

def get_ticket(conn, options):
	logging.info(get_ticket)
	baseurl='https://' + options["--ip"] + ':' + options["--ipport"]
	r = conn.get(baseurl, verify=False)
	if r.status_code != 200:
		r.close()
		return None
	postdata = {'username': options["--username"], 'password': options["--password"]}
	url=baseurl + '/api2/json/access/ticket'
	r = conn.post(url, json=postdata)
	if r.status_code != 200:
		r.close()
		return None    
	tdata=r.json()
	r.close()
	result=tdata["data"]
	return result


def main():
	atexit.register(atexit_handler)

	all_opt["node_name"] = {
		"getopt" : "N:",
		"longopt" : "nodename",
		"help" : "-N, --nodename                 "
			"Node on which machine is located",
		"required" : "0",
		"shortdesc" : "Node on which machine is located. "
			"(Optional, will be automatically determined)",
		"order": 2
	}

	device_opt = ["ipaddr", "login", "passwd", "web", "port", "node_name"]

	all_opt["login"]["required"] = "0"
	all_opt["login"]["default"] = "root@pam"
	all_opt["ipport"]["default"] = "8006"
	all_opt["port"]["shortdesc"] = "Id of the virtual machine."
	all_opt["ipaddr"]["shortdesc"] = "IP Address or Hostname of a node " +\
		"within the Proxmox cluster."

	options = check_input(device_opt, process_input(device_opt))
	docs = {}
	docs["shortdesc"] = "A simplified fencing agent for the Proxmox Virtual Environment"
	docs["longdesc"] = "The fence_proxmox agent can be used to fence virtual machines acting as nodes in a virtualized cluster."
	docs["vendorurl"] = "http://www.proxmox.com/"

	show_docs(options, docs)

	run_delay(options)

	if "--nodename" not in options or not options["--nodename"]:
		options["--nodename"] = None

	urllib3.disable_warnings()    

	conn = requests.Session()
	res = get_ticket(conn, options)
	if res is None:
		fail(EC_LOGIN_DENIED)
	
	options["--ticket"] = res["ticket"]
	options["--CSRFPreventionToken"] = res["CSRFPreventionToken"]
	
	result = fence_action(conn, options, set_power_status, get_power_status, get_outlet_list)

	sys.exit(result)

if __name__ == "__main__":
	main()
