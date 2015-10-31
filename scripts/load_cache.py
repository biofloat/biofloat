#!/usr/bin/env python

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parent_dir)

from oxyfloat import OxyFloat

class OxyFloatLoader(object):

    def process(self):
        of = OxyFloat(verbosity=2, cache_file=os.path.join(parent_dir, 'oxyfloat',
                      'oxyfloat_age_{}_max_profiles_{}.hdf'.format(
                            self.args.age, self.args.max_profiles)))

        floats340 = of.get_oxy_floats_from_status(age_gte=self.args.age)
        df = of.get_float_dataframe(floats340, max_profiles=self.args.max_profiles)

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example:' + '\n\n' 
        examples += sys.argv[0] + " --age 340 --max_profiles 20"
        examples += "\n"
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Script to load local HDF cache with Argo float data',
                                         epilog=examples)
                                             
        parser.add_argument('--age', action='store', help='Select age >=', type=int, default=340)
        parser.add_argument('--max_profiles', action='store', help='Maximum number of profiles', type=int)
        parser.add_argument('-v', '--verbose', nargs='?', choices=[0,1,2,3], type=int, 
                            help='Turn on verbose output. Higher number = more output.', const=2)

        self.args = parser.parse_args()


if __name__ == '__main__':

    ofl = OxyFloatLoader()
    ofl.process_command_line()
    ofl.process()

