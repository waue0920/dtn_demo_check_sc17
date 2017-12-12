#!/bin/bash

#export PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
#source /etc/profile 
#source ~/.bash_profile  

bin=`dirname "$0"`
bin=`cd "$bin"; pwd`
cd $bin;
from=$(date +%s)
starttime=$(date +%y%m%d_%H%M%S)

#/opt/rh/rh-python35/root/usr/bin/python3 ./dtn_demo_check_sc17v2.py > ./.tmp.data
/usr/bin/python3 ./dtn_demo_check_sc17v2.py > ./.tmp.data

now=$(date +%s)
total_time=$(expr $now - $from )

echo "$starttime | $total_time : "$(cat ./.tmp.data) >> run.log
