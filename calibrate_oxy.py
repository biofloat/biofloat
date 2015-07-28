#!/usr/bin/env python

from oxyfloat import get_oxy_floats, get_dac_urls

# This takes a few minutes
##oga_float_nums = get_oxy_floats()

# For testing
oga_float_nums = ['2902124', '2902123', '6901776']

dac_urls = get_dac_urls(oga_float_nums)

print dac_urls
