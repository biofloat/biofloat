#!/usr/bin/env python

import os
import sys
import unittest
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from oxyfloat import OxyFloat

class DataTest(unittest.TestCase):
    def setUp(self):
        self.of = OxyFloat(verbosity=2)
        self.good_oga_floats = ['1900650']
        self.bad_oga_floats = ['1901158']

    def test_get_oxyfloats(self):
        self.oga_floats = self.of.get_oxy_floats_from_status()
        self.assertNotEqual(len(self.oga_floats), 0)

    def _get_dac_urls(self):
        # Testing with a float that has data
        for dac_url in self.of.get_dac_urls(self.good_oga_floats).values():
            self.dac_url = dac_url
            self.assertTrue(self.dac_url.startswith('http'))
            break

    def _get_profile_opendap_urls(self):
        for profile_url in self.of.get_profile_opendap_urls(self.dac_url):
            self.profile_url = profile_url
            break

    def _profile_to_dataframe(self):
        d = self.of._profile_to_dataframe(self.good_oga_floats[0], 
                self.profile_url)
        self.assertNotEqual(len(d), 0)

    def test_read_profile_data(self):
        # Methods need to be called in order
        self._get_dac_urls()
        self._get_profile_opendap_urls()
        self._profile_to_dataframe()

    def test_get_float_dataframe(self):
        df = self.of.get_float_dataframe(self.good_oga_floats, 2)
        self.assertNotEqual(len(df), 0)
        df = self.of.get_float_dataframe(self.bad_oga_floats, 2)
        self.assertEqual(len(df), 0)

    def test_cache_file(self):
        of = OxyFloat(cache_file='/tmp/oxyfloat_cache_file.hdf')
        of.set_verbosity(1)

    def test_fixed_cache_file(self):
        age = 3000      # Returns 1 float on 2 November 2015
        parent_dir = os.path.join(os.path.dirname(__file__), "../")

        # Simulated what's done by load_cache.py
        from scripts.load_cache import OxyFloatLoader
        from argparse import Namespace
        ofl = OxyFloatLoader()
        ofl.args = Namespace(age=3000, profiles=1)
        cache_file = os.path.abspath(
                     os.path.join(parent_dir, 'oxyfloat', ofl.short_cache_file()))

        of = OxyFloat(verbosity=2, cache_file=cache_file)
        wmo_list = of.get_oxy_floats_from_status(age_gte=age)
        # Force limiting to what's in cache_file name: 1
        of.get_float_dataframe(wmo_list, max_profiles=2)
        # Force using of._MAX_PROFILES
        of.get_float_dataframe(wmo_list)
        
if __name__ == '__main__':
    unittest.main()
