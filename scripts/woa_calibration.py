#!/usr/bin/env python

import sys
from os.path import join, dirname, abspath, expanduser
parent_dir = join(dirname(__file__), "../")
sys.path.insert(0, parent_dir)

import logging
import matplotlib as plt
import pandas as pd
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

    def __init__(self):
        self._woa_lookup_count = 0

    def make_plot(self):
        plt.style.use('ggplot')
        plt.rcParams['figure.figsize'] = (18.0, 4.0)
        gdf[['o2sat', 'woa_o2sat']].unstack(level=0).plot()
        gdf[['gain']].unstack(level=0).plot()


    def woa_lookup(self, df):
        '''Given a DataFrame of profile data for an Argo float as read from
        a biofloat cache file, average the data to the spatial temporal
        grid of the World Ocean Atlas and return a DataFrame with float
        and WOA O2 saturation columns added.  The WOA lookup goes across
        the Internet so can take a minute or so to lookup all the values.
        '''
        gdf = pd.DataFrame([pd.np.nan])
        sdf = surface_mean(df)
        sdf = add_columns_for_groupby(sdf)
        msdf = monthly_mean(sdf)
        if not msdf.empty:
            msdf = add_columns_for_woa_lookup(msdf)
            self._woa_lookup_count += len(msdf)
            self.logger.info('Doing WOA lookup for %s points; total lookups: %s', 
                             len(msdf), self._woa_lookup_count)
            woadf = add_column_from_woa(msdf, verbose=(self.args.print_woa_lookups 
                                                   and self.args.verbose))
            gdf = calculate_gain(woadf)

        return gdf

    def process(self):
        self.logger.setLevel(self._log_levels[self.args.verbose])
        ad = ArgoData(verbosity=self.args.verbose, 
                      cache_file=self.args.cache_file)

        if self.args.wmo:
            wmo_list = self.args.wmo
        else:
            wmo_list = ad.get_cache_file_oxy_count_df()['wmo'].tolist()

        self.logger.info('Reading float profile data from %s', self.args.cache_file)
        for i, wmo in enumerate(wmo_list):
            self.logger.info('WMO_%s: Float %s of %s', wmo, i+1, len(wmo_list))
            try:
                with pd.HDFStore(self.args.results_file) as s:
                    self.logger.debug('Reading %s from %s', ('/WOA_WMO_{}').format(wmo),
                                                             self.args.cache_file)
                    wmo_gdf = s.get(('/WOA_WMO_{}').format(wmo))
                    self.logger.debug('Done.')
            except KeyError:
                df = ad.get_float_dataframe([wmo],
                                            max_profiles=self.args.profiles, 
                                            max_pressure=self.args.pressure,
                                            update_cache=False)
                wmo_gdf = self.woa_lookup(df)

                if not wmo_gdf.dropna().empty:
                    # Save intermediate results to HDF file so that the script can
                    # pick up where it left off following network or other problems
                    with pd.HDFStore(self.args.results_file) as s:
                        s.put(('/WOA_WMO_{}').format(wmo), wmo_gdf)
                else:
                    self.logger.warn('Empty DataFrame for wmo %s', wmo)

            if not wmo_gdf.dropna().empty:
                self.logger.debug('wmo_gdf head: %s', wmo_gdf.head())
                self.logger.info('Gain for %s = %s', wmo, 
                                 wmo_gdf.groupby('wmo').gain.mean().values[0])

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
        parser.add_argument('--print_woa_lookups', action='store_true', 
                                     help='In conjunction with -v print WOA lookups')
        parser.add_argument('--results_file', action='store', required=True,
                             help='File name for float and woa surface saturation values')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[0,1,2,3], type=int,
                            help='0: ERROR, 1: WARN, 2: INFO, 3:DEBUG', default=0, const=2)

        self.args = parser.parse_args()


if __name__ == '__main__':

    woac = WOA_Calibrator()
    woac.process_command_line()
    woac.process()

