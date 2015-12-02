#!/bin/bash
# Watch the execution of a long-running load_biofloat_cache.py job
# and restart it if its log file hasn't been updated in 10 minutes
# or so,  Check last line for completion before restarting.  The arguemnts
# are: <log_file_name> <load_biofloat_cache.py command with all arguments>.
#
# Execute from cron like:
# * */10 * * *  load_biofloat_cache_watchdog.sh /u/mccann/dev/biofloatgit/cache_age364_MR_dropna.out /u/mccann/dev/biofloatgit/scripts/load_biofloat_cache.py --age 364 --cache_dir /data/biofloat -v > /dev/null 2>&1

######## Change these for your installation
email_address=mccann
venv_dir=/u/mccann/dev/biofloatgit/venv-biofloat
########

log_file=$(echo $@ | cut -d ' ' -f 1)
shift
lbc_cmd=$@
shift
lbc_args=$@

# Escape special characters as needed by awk search
lbc_args=$(echo $lbc_args | sed -e 's/[.:\/&]/\\&/g')

ct=$(date +"%s")
ft=$(stat -c %Y $log_file)
log_file_age=$((ct - ft))

if [ $log_file_age -gt 600 ]
then
    echo Paused
    last_line=$(tail -1 $log_file)
    echo -e "$lbc_cmd has paused.  Attempting to kill and restart.\n$last_line" | mail -s $log_file $email_address
    # Can't seem to grep for $lbc_args, grep for load_biofloat_cache.py instead
    pid0=$(ps -ef | awk "/$lbc_args/" | grep -v bash | grep -v grep | awk -F' ' '{print $2}')
    pid=$(ps -ef | grep load_biofloat_cache.py | grep -v bash | grep -v grep | awk -F' ' '{print $2}')
    if [ ! -z $pid ]
    then
        echo pid0: $pid0
        echo Killing $pid
        kill $pid
    fi
    first_word=$(echo $last_line | cut -d ' ' -f 1)
    if [ ! "$first_word" == "Finished" ]
    then
        echo Restarting python $lbc_cmd 
        source $venv_dir/bin/activate
        python $lbc_cmd >> $log_file 2>&1 &
    else
        echo "$lbc_cmd appears to have finished. You can cancel this cron job." | mail -s $log_file $email_address
    fi
fi

