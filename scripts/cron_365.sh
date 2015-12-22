#!/bin/bash
# Script to execute from cron in the early hours of the morning
# to update local biofloat cache with new profile data.
# Copies the cache file to anonymous FTP and saves a daily log file.
#
# Execute from cron like:
# 0 2 * * *  dev/biofloatgit/scripts/cron_365.sh

######## Change these for your installation
biofloat_dir=/u/mccann/dev/biofloatgit
work_dir=/data/biofloat
ftp_dir=/mbari/FTP/pub/biofloat
########

log_file=$biofloat_dir/logs/cron_365_$(date +%Y%m%d).out
source $biofloat_dir/venv-biofloat/bin/activate
python $biofloat_dir/scripts/load_biofloat_cache.py --age 365 --cache_dir $work_dir -v > $log_file 2>&1
cp /data/biofloat/biofloat_fixed_cache_age365_variablesDOXY_ADJUSTED-PSAL_ADJUSTED-TEMP_ADJUSTED.hdf $ftp_dir
