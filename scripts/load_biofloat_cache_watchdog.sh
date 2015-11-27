#!/bin/bash
# Watch the execution of a long-running load_biofloat_cache.py job
# and restart it if its log file hasn't been updated in 10 minutes
# or so,  Check last line for completion before restarting.
#
# Execute from cron like:
# * */10 * * *  load_biofloat_cache_watchdog.sh /u/mccann/dev/biofloatgit/cache_age365_MR_dropna.out /u/mccann/dev/biofloatgit/scripts/load_biofloat_cache.py --age 364 --cache_dir /data/biofloat -v

log_file=$(echo $@ | cut -d ' ' -f 1)
shift
lbc_cmd=$@
shift
lbc_args=$@

ct=$(date +"%s")
ft=$(stat -c %Y $log_file)

log_file_age=$((ct - ft))
##echo $log_file_age
if [ $log_file_age -gt 600 ]
then
    echo Paused
    echo "$lbc_cmd  has paused.  Attempting to kill and restart." | mail -s $log_file mccann
    # Can't seem to grep for $lbc_args, grep for load_biofloat_cache.py instead
    ##pid=$(ps -ef | grep "\"$lbc_args\"" | awk -F' ' '{print $2}')
    pid=$(ps -ef | grep load_biofloat_cache.py | grep -v bash | grep -v grep | awk -F' ' '{print $2}')
    echo killing $pid
    kill $pid
    echo restarting python $lbc_cmd 
    source /u/mccann/dev/biofloatgit/venv-biofloat/bin/activate
    python $lbc_cmd >> $log_file 2>&1 &
fi
