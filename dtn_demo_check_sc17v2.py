#!/usr/bin/env python3
### readme
### run the script in sudoer priviledge ! ( or get exception)

#
# json_str = json.dumps(data)
#
# print(json_str)
#
# with open('data.json', 'w') as f :
#    json.dump(data,f)
#
# with open('data.json', 'r') as f :
#    data1 = json.load(f)
#
# from pprint import pprint
# pprint(data1)

import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import re
## global
server_list = [
    (3060, "192.168.60.57"),
    (3061, "192.168.61.57"),
    (3062, "192.168.62.59"),
    (3063, "192.168.63.59"),
    (1038, "10.250.38.50"),
]
file_list = [
    "/data/disk0/sc17/fftest",
    "/data/disk1/sc17/fftest",
    "/data/disk2/sc17/fftest",
    "/data/disk3/sc17/fftest",
    "/data/disk4/sc17/fftest",
    "/data/disk5/sc17/fftest",
    "/data/disk6/sc17/fftest",
    "/data/disk7/sc17/fftest",
]
dir_list = [
    "/data/disk0/sc17/",
    "/data/disk1/sc17/",
    "/data/disk2/sc17/",
    "/data/disk3/sc17/",
    "/data/disk4/sc17/",
    "/data/disk5/sc17/",
    "/data/disk6/sc17/",
    "/data/disk7/sc17/",
]
result_json="./dtn_demo_check_sc17.json"

## function

def return_command(cmd):
    #  return execution result as output -> str
    process = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=1)
    return process.stdout.read().decode('utf8')


def check_command_old(cmd):
    #  return 0 if success, or return > 0 -> int
    return os.system(cmd)


def check_command(cmd):
    #  return 0 if success, or return > 0 -> int
    process = subprocess.run(cmd)
    return process.returncode


def checkFirewall():
    # check iptables is existed, if without iptables, pass the check
    if shutil.which("iptables") is None:
        return 1

    ret = return_command("head -n 1 /etc/os-release")
    # check Centos or Ubuntu, only Centos iptables filter 8000 ..
    # if re.search("CentOS Linux", ret) == None: # easily failed
    if "CentOS" in ret:
        # if Centos , check the rule for opening 8000 port for jupyter
        ret = return_command("iptables -nvL |grep 8000 |wc -l")
        if int(ret) < 1:
            return 0
    return 1


def checkVlan():
    vlan63 = "192.168.63.59"
    vlan61 = "192.168.61.57"
    # check vlan 61 and 63

    if int(check_command("ping -c 1 " + vlan63 + ">/dev/null")) != 0:
        # vlan 63 can't connect, check 61
        if int(check_command("ping -c 1 " + vlan61 + ">/dev/null")) != 0:
            # neither 61 nor 63 is failed to ping, return 0
            return 0
        else:
            return 61
    else:
        # vlan 63 ok , check 61
        if int(check_command("ping -c 1 " + vlan61 + ">/dev/null")) != 0:
            # vlan 63 ok, check 61 failed
            return 63
        else:
            # both 61 nor 63 is ok to ping
            return 6163


def checkJupyter():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # check the jupyter port is open, because system reboot will reset iptables rules
    ret = sock.connect_ex(('0.0.0.0', 8000))
    if ret != 0:
        return 0
    return 1


def checkNvme():
    ret = int(return_command("df |grep nvme |wc -l "))
    if type(ret) == int:
        return int(ret)
    else:
        return 0


def checkFileExist():

    ### this will occur file not found exection
    #   ret = return_command("ls /data/disk*/sc17/fftest | wc -l ")
    #   if int(ret) < 8:
    #       return 0
    #   return 1
    global file_list
    count = 0

    for fd in file_list:
        if os.access(fd, os.R_OK) is False:
            continue
        count += 1
    return count


def checkDirPermission():
    count = 0
    global dir_list
    for fd in dir_list:
        if os.access(fd, os.W_OK) is False:
            continue
        count += 1
    return count


checklist = {}
# checklist = {
#    'firewall_check': 1,
#    'vlan_check': 1,
#    'jupyter_check': 1,
#    'nvme_check': 1,
#    'directory_check': 1,
#    'permission_check': 1,
# }

def checkSudoer():
    if os.getuid() != 0:
        return False
    else:
        return True


def pingServer(server, qu):
    vlan_name = server[0]
    server_name = server[1]
    if int(check_command(["ping", "-c 1", server_name + " >/dev/null"])) == 0:

        # result = subprocess.run(["/sbin/ping", "-c 1", server])
        # if result.returncode == 0 :

        # success
        qu.put((vlan_name, 1))
    else:
        # failed
        qu.put((vlan_name, 0))


def checkIndVlan():
    global server_list
    ret = {}
    qu = queue.Queue()

    # threads = [None,None,None,None,None]
    threads = []

    for i in range(len(server_list)):
        server = server_list[i]
        # threads[i] = threading.Thread(target=pingServer, args=(server,qu))
        # threads[i].start()
        th = threading.Thread(target=pingServer, args=(server, qu))
        th.start()
        threads.append(th)

    # for i in range(len(server_list)):
    #     threads[i].join()
    while (len(threads) != 0):
        th = threads.pop()
        th.join()

    while (qu.empty() is False):
        vlan_ret = qu.get()
        # vlan_ret[0] = 3060, ...
        # vlan_ret[1] = 1 or 0
        ret[vlan_ret[0]] = vlan_ret[1]

    return ret

def cmd_exec(cmd):
    process = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    return process.stdout.read().decode('utf8')

def nvme_query(nvme_name):

    command = "nvme smart-log " + nvme_name
    ret =  cmd_exec(command)
    return ret


def get_nvme_list():
    query=cmd_exec("nvme list")

    result_list=[]
    for line in query.splitlines():
        if "nvme" in line :
            m= re.match(r'^(\S+)\s+.+$', line)
            result_list.append(m.group(1))

    return result_list


def checkNvmeTemp():
    ret={}
    dev_list= get_nvme_list()
    for nvme_name in dev_list:
        get_result=nvme_query(nvme_name)
        for line in get_result.splitlines():
            if "temperature" in line :
                m = re.match(r'temperature:(\d+)C', line.strip().replace(" ",""))
                t_val = m.group(1)
    #            print(" {:10s} : {:10s}  ".format(nvme_name, t_val))
                ret[nvme_name]=int(t_val)
    return ret

def main():
    checklist["firewall_check"] = checkFirewall()

    checklist["vlan_check"] = checkVlan() ## deprecated
    ## need use python 3.5 and may failed by crontab
    #checklist["vlan_check"] = checkIndVlan()

    checklist["jupyter_check"] = checkJupyter()
    checklist["nvme_check"] = checkNvme()
    checklist["testfile_check"] = checkFileExist()
    checklist["permission_check"] = checkDirPermission()
    checklist["nvme_heat_check"] = checkNvmeTemp()
    json_str = json.dumps(checklist, indent=4)
    print(json_str)
    with open(result_json, "w") as f:
        f.write(json_str)


def usage():
    print("{msg=\"You should run this in sudo priviledge !\"}")
    exit(1)


if __name__ == "__main__":
    main()
    # usage() if checkSudoer() is False else main()

