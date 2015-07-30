#!/usr/bin/env python

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
oga_float_nums = ['1900650', '1901378', '1900722', '2902124', '2902123', '6901776']
test_file = 'D1900650_137.nc'

# Create a MongoDB document database for storing the profile data
client = MongoClient()
db = client.oxyfloat
floats = db.floats

for dac_url in of.get_dac_urls(oga_float_nums):
    float = dac_url.split('/')[6]
    for profile_url in sorted(of.get_profile_opendap_urls(dac_url)):
        if test_file:
            if not profile_url.endswith(test_file):
                continue
        logger.info('Reading data from ...' + profile_url[20:])
        try:
            d = of.get_profile_data(profile_url)
        except RequiredVariableNotPresent as e:
            logger.warn(e)
        except OpenDAPServerError as e:
            logger.warn(e)
        else:
            prof = str(profile_url.split('/')[-1].split('.')[0].split('_')[1])
            float_data = {float: {prof: d}}
            id = floats.insert_one(float_data).inserted_id
            logger.debug('ID ' + str(id) + ' stored in mongodb floats database')


