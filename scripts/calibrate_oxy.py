#!/usr/bin/env python

import os
import sys
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from pymongo import MongoClient
from oxyfloat import OxyFloat, RequiredVariableNotPresent, OpenDAPServerError

import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()

formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                              '%(funcName)s():%(lineno)d %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

of = OxyFloat(debug=True)

# This takes a few minutes to build the list of the desired floats
##oga_float_nums = of.get_oxy_floats()

# We can use a few numbers for testing
logger.debug('Using test oga_float_nums...')
oga_float_nums = ['1900650']
test_file = 'D1900650_137.nc'

# Create a MongoDB document database for storing the profile data
client = MongoClient()
db = client.oxyfloat
floats = db.floats

# Crawl the Argo/Ifremer sites to load data into local database
##for dac_url in of.get_dac_urls(oga_float_nums):
    ##pd = of.get_data_for_float(dac_url, only_file=None)
    ##if pd:
    ##    of.db_insert_float_data(pd)

# Pull out all of the latitude/longitude pairs
geoms = db.floats.find(projection={'lat.lon':1})
for geom in geoms:
    print geom

