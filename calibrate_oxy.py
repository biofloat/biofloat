#!/usr/bin/env python

import oxyfloat
import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()

formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                              '%(funcName)s():%(lineno)d %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

# This takes a few minutes to build the list of the desired floats
oga_float_nums = oxyfloat.get_oxy_floats()

# We can use a few numbers for testing
##logger.debug('Using test oga_float_nums...')
##oga_float_nums = ['1900722', '2902124', '2902123', '6901776']

for dac_url in oxyfloat.get_dac_urls(oga_float_nums):
    for profile_url in oxyfloat.get_profile_opendap_urls(dac_url,
            use_beautifulsoup=True):
        logger.info('Reading data from ...%s', profile_url[20:])
        try:
            float_data = oxyfloat.get_profile_data(profile_url)
        except oxyfloat.RequiredVariableNotPresent as e:
            logger.warn(e)
        except oxyfloat.OpenDAPServerError as e:
            logger.warn(e)
        else:
            print float_data


