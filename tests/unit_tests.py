#!/usr/bin/env python

import os
import sys
import unittest
parentDir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parentDir)

from oxyfloat import OxyFloat

class DataTest(unittest.TestCase):
    def setUp(self):
        self.of = OxyFloat(verbosity=3)

    def test_get_oxyfloats(self):
        self.oga_floats = self.of.get_oxy_floats()
        self.assertNotEqual(len(self.oga_floats), 0)

    def _get_dac_urls(self):
        # Testing with a float that has data
        oga_floats = ['1900650']
        for dac_url in self.of.get_dac_urls(oga_floats):
            self.dac_url = dac_url
            self.assertTrue(self.dac_url.startswith('http'))
            break

    def _get_profile_opendap_urls(self):
        for profile_url in self.of.get_profile_opendap_urls(self.dac_url):
            self.profile_url = profile_url
            break

    def _get_profile_data(self):
        ds = self.of.get_profile_data(self.profile_url, surface_values_only=True)
        self.assertNotEqual(len(ds), 0)
        d = self.of.get_profile_data(self.profile_url)
        self.assertNotEqual(len(d), 0)

    def test_read_profile_data(self):
        # Methods need to be called in order
        self._get_dac_urls()
        self._get_profile_opendap_urls()
        self._get_profile_data()

    def test_get_data_for_float(self):
        dac_url = 'http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBSaoml/1900722/profiles/catalog.xml'
        # This takes a long time to run so specify an only_file
        self.of.get_data_for_float(dac_url, only_file='MD1900722_135.nc')

if __name__ == '__main__':
    unittest.main()
