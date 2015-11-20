#!/usr/bin/env python

import sys
from os.path import join, dirname, abspath, expanduser
parent_dir = join(dirname(__file__), "../")
sys.path.insert(0, parent_dir)

import logging
import matplotlib as plt
import xray

from biofloat import ArgoData
from biofloat.utils import o2sat, convert_to_mll
from biofloat.calibrate import (woa_o2sat, surface_mean, monthly_mean, 
                                add_columns_for_groupby, add_columns_for_woa_lookup,
                                add_column_from_woa, calculate_gain
                               )

class WOA_Calibrator(object):

    logger = logging.getLogger(__name__)
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                  '%(funcName)s():%(lineno)d %(message)s')
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)

    _log_levels = (logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG)

    def make_plot(self):
        plt.style.use('ggplot')
        plt.rcParams['figure.figsize'] = (18.0, 4.0)
        gdf[['o2sat', 'woa_o2sat']].unstack(level=0).plot()
        gdf[['gain']].unstack(level=0).plot()



    def process(self):
        self.logger.setLevel(self._log_levels[self.args.verbose])
        ad = ArgoData(verbosity=self.args.verbose, 
                      cache_file=self.args.cache_file)

        if self.args.wmo:
            wmo_list = self.args.wmo
        else:
            wmo_list = ad.get_cache_file_oxy_count_df()['wmo'].tolist()

        for wmo in wmo_list:
            self.logger.info('Reading float %s from %s', wmo, self.args.cache_file)
            df = ad.get_float_dataframe([wmo],
                                        max_profiles=self.args.profiles, 
                                        max_pressure=self.args.pressure)

            sdf = surface_mean(df)
            sdf = add_columns_for_groupby(sdf)
            msdf = monthly_mean(sdf)
            msdf = add_columns_for_woa_lookup(msdf)
            self.logger.info('Doing WOA lookup')
            woadf = add_column_from_woa(msdf)
            gdf = calculate_gain(woadf)

            print(gdf.groupby('wmo').gain.mean())

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n' 
        examples += '---------' + '\n' 
        examples += sys.argv[0] + " --cache_file /data/biofloat/biofloat_fixed_cache_age365.hdf\n"
        examples += "\n\n"
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                    description='Script to compare surface oxygen saturation values\n'
                                'with data from the World Ocean Atlas and calculate\n'
                                'a gain factor that can be used to calibrate Bio-Argo\n'
                                'float measurements.',
                    epilog=examples)
                                             
        parser.add_argument('--cache_file', action='store', help='full path to cache file',
                                            required=True)
        parser.add_argument('--wmo', action='store', nargs='*', default=[],
                                     help='One or more WMO numbers to read from cache file')
        parser.add_argument('--profiles', action='store', 
                                     help='Maximum number of profiles to read in')
        parser.add_argument('--pressure', action='store', 
                                     help='Maximum pressure to read in')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[0,1,2,3], type=int,
                            help='0: ERROR, 1: WARN, 2: INFO, 3:DEBUG', default=0, const=2)

        self.args = parser.parse_args()


if __name__ == '__main__':

    woac = WOA_Calibrator()
    woac.process_command_line()
    woac.process()

