import os
import re
import logging
import urllib2
import requests
import pandas as pd
import pydap.client
import pydap.exceptions
import xray

from bs4 import BeautifulSoup
from collections import namedtuple
from contextlib import closing
from datetime import datetime
from requests.exceptions import ConnectionError
from shutil import move

# Support Python 2.7 and 3.x
try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO

from exceptions import RequiredVariableNotPresent

class ArgoData(object):
    '''Collection of methods for working with Argo profiling float data.
    '''

    # Jupyter Notebook defines a root logger, use that if it exists
    if logging.getLogger().handlers:
        _notebook_handler = logging.getLogger().handlers[0]
        logger = logging.getLogger()
    else:
        logger = logging.getLogger(__name__)
        _handler = logging.StreamHandler()
        _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                      '%(funcName)s():%(lineno)d %(message)s')
        _handler.setFormatter(_formatter)
        logger.addHandler(_handler)

    _log_levels = (logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG)

    # Literals for groups stored in local HDF file cache
    _STATUS = 'status'
    _GLOBAL_META = 'global_meta'
    _BIO_PROFILE_INDEX = 'bio_global_index'
    _ALL_WMO_DF = 'all_wmo_df'
    _OXY_COUNT_DF = 'oxy_count_df'
    _coordinates = {'PRES_ADJUSTED', 'LATITUDE', 'LONGITUDE', 'JULD'}

    # Names and search patterns for cache file naming/parsing
    # Make private and ignore pylint's complaints
    # No other names in this class can end in 'RE'
    _fixed_cache_base = 'biofloat_fixed_cache'
    _ageRE = 'age([0-9]+)'
    _profilesRE = 'profiles([0-9]+)'
    _pressureRE = 'pressure([0-9]+)'
    _wmoRE = 'wmo([0-9-]+)'
    _variablesRE = 'var([0-9-]+)'

    _MAX_VALUE = 10000000000
    _compparms = dict(complib='zlib', complevel=9)

    # PyTables: Use non-empty minimal df to minimize HDF file size
    _blank_df = pd.DataFrame([pd.np.nan])

    def __init__(self, verbosity=0, cache_file=None, bio_list=('DOXY_ADJUSTED',),
            status_url='http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt',
            global_url='ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt',
            thredds_url='http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS',
            variables=('TEMP_ADJUSTED', 'PSAL_ADJUSTED', 'DOXY_ADJUSTED')):

        '''Initialize ArgoData object.
        
        Args:
            verbosity (int): range(4), default=0
            cache_file (str): Defaults to biofloat_default_cache.hdf in users
                              home directory
            bio_list (list): List of required bio variables, e.g.:
                             ['DOXY_ADJUSTED', 'CHLA', 'BBP700', 'CDOM', 'NITRATE']
            status_url (str): Source URL for Argo status data, defaults to
                              http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt
            global_url (str): Source URL for DAC locations, defaults to
                              ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt
            thredds_url (str): Base URL for THREDDS Data Server, defaults to
                               http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS
            variables (list): Variables to extract from NetCDF files and put
                              into the Pandas DataFrame

            cache_file (str):

            There are 3 kinds of cache files:

            1. The default file named biofloat_cache.hdf that is automatically
               placed in the user's home directory. It will cache whatever
               data is requested via call to get_float_dataframe().
            2. Specially named cache_files produced by the load_biofloat_cache.py
               script. These files are built with constraints and are fixed. 
               Once built they can be used in a read-only fashion to work on 
               only the data they contain. Calls to get_float_dataframe().
               will not add more data to these "fixed" cache files.
            3. Custom cache file names. These operate just like the default cache
               file, but can be named whatever the user wants. 

        '''
        self.status_url = status_url
        self.global_url = global_url
        self.thredds_url = thredds_url
        self.variables = set(variables)

        self.logger.setLevel(self._log_levels[verbosity])
        self._bio_list = bio_list

        if cache_file:
            self.cache_file_parms = self._get_cache_file_parms(cache_file)
            if self.cache_file_parms:
                self.logger.info('Using fixed cache file parms: %s', 
                                 self.cache_file_parms)
            self.cache_file = cache_file
        else:
            # Write default cache to users home directory 
            self.cache_file = os.path.abspath(os.path.join(
                              os.path.expanduser('~'), 
                              'biofloat_default_cache.hdf'))

        self.logger.info('Using cache_file %s', self.cache_file)

    def _put_df(self, df, name, metadata=None):
        '''Save Pandas DataFrame to local HDF file with optional metadata dict.
        '''
        store = pd.HDFStore(self.cache_file)
        self.logger.debug('Saving DataFrame to name "%s" in file %s',
                                              name, self.cache_file)
        if df.dropna().empty:
            store.put(name, df, format='fixed')
        else:
            ##store.append(name, df, format='table', **self._compparms)
            store.put(name, df, format='fixed')

        if metadata and store.get_storer(name):
            store.get_storer(name).attrs.metadata = metadata

        self.logger.debug('store.close()')
        store.close()

    def _get_df(self, name):
        '''Return tuple of Pandas DataFrame and metadata dictionary.
        '''
        store = pd.HDFStore(self.cache_file)
        try:
            self.logger.debug('Getting "%s" from %s', name, self.cache_file)
            df = store[name]
            try:
                metadata = store.get_storer(name).attrs.metadata
            except AttributeError:
                metadata = None
        except (IOError, KeyError):
            raise
        finally:
            self.logger.debug('store.close()')
            store.close()

        return df, metadata

    def _remove_df(self, name):
        '''Remove name from cache file
        '''
        with pd.HDFStore(self.cache_file) as store:
            self.logger.debug('Removing "%s" from %s', name, self.cache_file)
            store.remove(name)

    def _status_to_df(self):
        '''Read the data at status_url link and return it as a Pandas DataFrame.
        '''
        self.logger.info('Reading data from %s', self.status_url)
        req = requests.get(self.status_url)
        req.encoding = 'UTF-16LE'

        # Had to tell requests the encoding, StringIO makes the text 
        # look like a file object. Skip over leading BOM bytes.
        df = pd.read_csv(StringIO(req.text[1:]))
        return df

    def _ftp_csv_to_df(self, url, date_columns=[]):
        '''Read the data at url link and return it as a Pandas DataFrame.
        '''
        self.logger.info('Reading data from %s', url)
        with closing(urllib2.urlopen(url)) as r:
            df = pd.read_csv(r, comment='#', parse_dates=date_columns)

        return df

    def _get_pressures(self, ds, max_pressure, nprof=0):
        '''From xray ds return tuple of pressures list and pres_indices list.
        '''
        pressures = []
        pres_indices = []
        for i, p in enumerate(ds['PRES_ADJUSTED'].values[nprof]):
            if p >= max_pressure:
                break
            pressures.append(p)
            pres_indices.append(i)

        if not pressures:
            self.logger.warn('No PRES_ADJUSTED values in netCDF file')

        return pressures, pres_indices

    def _multi_indices(self, wmo, ds, max_pressure, profile, nprof=0):
        '''Return list of tuples that is used for Pandas MultiIndex hireachical 
        index and indices to pressure variable.
        '''
        pressures = []
        pres_indices = []
        try:
            pressures, pres_indices = self._get_pressures(ds, max_pressure, nprof)
        except pydap.exceptions.ServerError as e:
            self.logger.error(e)
        except IndexError:
            self.logger.warn('Profile [%s] does not exist', nprof)

        # Make a DataFrame with a hierarchical index for better efficiency
        # Argo data have a N_PROF dimension always of length 1, hence the [0]
        tuples = [(wmo, ds['JULD'].values[nprof], ds['LONGITUDE'].values[nprof], 
                        ds['LATITUDE'].values[nprof], profile, round(pres, 2))
                                        for pres in pressures]
        indices = pd.MultiIndex.from_tuples(tuples, 
                names=['wmo', 'time', 'lon', 'lat', 'profile', 'pressure'])

        return indices, pres_indices

    def _build_profile_dataframe(self, wmo, url, ds, max_pressure, profile, nprof):
        '''Return DataFrame containing the variables from N_PROF column in
        url specified by nprof integer (0,1).
        '''
        df = pd.DataFrame()
        # Add only non-coordinate variables to the DataFrame
        for v in self.variables:
            try:
                indices, pres_indices = self._multi_indices(wmo, ds, 
                                             max_pressure, profile, nprof)
                s = pd.Series(ds[v].values[nprof][pres_indices], index=indices)
                self.logger.debug('Added %s to DataFrame', v)
                df[v] = s
            except (KeyError, TypeError):
                self.logger.warn('%s not in %s', v, url)
            except pydap.exceptions.ServerError as e:
                self.logger.error(e)

        return df

    def _profile_to_dataframe(self, wmo, url, key, max_pressure):
        '''Return a Pandas DataFrame of profiling float data from data at url.
        Examine data at url for variables in self._bio_list that may be in 
        the lower vertical resolution [1] N_PROF array.
        '''
        df = self._blank_df
        try:
            self.logger.debug('Opening %s', url)
            ds = xray.open_dataset(url)
        except pydap.exceptions.ServerError:
            self.logger.error('ServerError opening %s', url)
            return df
        except Exception as e:
            self.logger.error('Error opening %s: %s', url, str(e))
            return df

        self.logger.debug('Checking %s for our desired variables', url)
        for v in self._coordinates.union(self.variables):
            if v not in ds.keys():
                raise RequiredVariableNotPresent('{} not in {}'.format(v, url))

        profile = int(key.split('P')[1])

        df = self._build_profile_dataframe(wmo, url, ds, max_pressure, 
                                           profile, nprof=0)

        # Check for required bio variables - should only the low resolution 
        # data be returned or should the high resolution T/S data be 
        # concatenated with the lower vertical resolution variables?
        for var in self._bio_list:
            if df[var].dropna().empty:
                self.logger.warn('%s: N_PROF [0] empty, trying [1]', var)
                df = self._build_profile_dataframe(wmo, url, ds, max_pressure, 
                                                   profile, nprof=1)

        return df

    def _get_update_datetime(self, url):
        '''Return python datetime of DATE_UPDATE variable from NetCDF file at url
        '''
        dt = None
        try:
            self.logger.debug('Opening %s', url)
            ds = xray.open_dataset(url)
        except pydap.exceptions.ServerError:
            self.logger.error('ServerError opening %s', url)
            return dt

        dt = datetime.strptime(ds['DATE_UPDATE'].values, '%Y%m%d%H%M%S')

        return dt

    def _float_profile_key(self, url):
        '''Return last part of url as key that serves as a PyTables/HDF 
        group name: WMO_<wmo>/P<profilenumber>. The parent group WMO_<wmo>
        must be created before this key can be used to put data.
        '''
        regex = re.compile(r"([a-zA-Z]+)(\d+_\d+).nc$")
        m = regex.search(url)
        key = '/WMO_{:s}'.format(m.group(2).replace('_', '/P'))
        code = m.group(1)

        return key, code

    def set_verbosity(self, verbosity):
        '''Change loglevel. 0: ERROR, 1: WARN, 2: INFO, 3:DEBUG.
        '''
        self.logger.setLevel(self._log_levels[verbosity])

    def get_oxy_floats_from_status(self, age_gte=340):
        '''Return a Pandas Series of floats that are identified to have oxygen,
        are not greylisted, and have an age greater or equal to age_gte. 

        Args:
            age_gte (int): Restrict to floats with data >= age, defaults to 340
        '''
        try:
            df, _ = self._get_df(self._STATUS)
        except (IOError, KeyError):
            self.logger.debug('Could not read status from cache, loading it.')
            self._put_df(self._status_to_df(), self._STATUS)
            df, _ = self._get_df(self._STATUS)

        odf = df.query('(OXYGEN == 1) & (GREYLIST == 0) & (AGE != 0) & '
                       '(AGE >= {:d})'.format(age_gte))

        return odf['WMO'].tolist()

    def get_dac_urls(self, wmo_list):
        '''Return dictionary of Data Assembly Centers keyed by wmo number.

        Args:
            wmo_list (list[str]): List of strings of float numbers
        '''
        try:
            df, _ = self._get_df(self._GLOBAL_META)
        except KeyError:
            self.logger.debug('Could not read global_meta, putting it into cache.')
            self._put_df(self._ftp_csv_to_df(self.global_url, 
                              date_columns=['date_update']), self._GLOBAL_META)
            df, _ = self._get_df(self._GLOBAL_META)

        dac_urls = {}
        for _, row in df.loc[:,['file']].iterrows():
            wmo = row['file'].split('/')[1]
            if wmo in wmo_list:
                url = self.thredds_url
                url += '/'.join(row['file'].split('/')[:2])
                url += "/profiles/catalog.xml"
                dac_urls[wmo] = url

        self.logger.debug('Found %s dac_urls', len(dac_urls))

        return dac_urls

    def get_bio_profile_index(self,
            url='ftp://ftp.ifremer.fr/ifremer/argo/argo_bio-profile_index.txt'):
        '''Return Pandas DataFrame of data at url
        '''
        try:
            df, _ = self._get_df(self._BIO_PROFILE_INDEX)
        except KeyError:
            self.logger.debug('Adding %s to cache', self._BIO_PROFILE_INDEX)
            self._put_df(self._ftp_csv_to_df(url, date_columns=['date', 'date_update']),
                         self._BIO_PROFILE_INDEX)
            df, _ = self._get_df(self._BIO_PROFILE_INDEX)

        return df

    def _sort_opendap_urls(self, urls):
        '''Organize list of Argo OpenDAP URLs so that 'D' Delayed Mode or
        urls that contain 'D' appear before 'R' Realtime ones.
        '''
        durls = []
        hasdurls = []
        mrurls = []
        rurls = []
        for url in urls:
            regex = re.compile(r"([a-zA-Z]+)\d+_\d+.nc$")
            try:
                code = regex.search(url).group(1).upper()
            except AttributeError:
                continue
            if 'D' == code:
                durls.append(url)
            elif 'D' in code:
                hasdurls.append(url)
            elif 'MR' == code:
                mrurls.append(url)
            else:
                rurls.append(url)

        # Return each group in reverse order, as they appear on the TDS
        return sorted(durls, reverse=True) + sorted(hasdurls, reverse=True
                ) + sorted(mrurls, reverse=True) + sorted(rurls, reverse=True)

    def get_profile_opendap_urls(self, catalog_url):
        '''Returns list of opendap urls for the profiles in catalog. The 
        list is ordered with Delayed mode versions before Realtime ones.
        The `catalog_url` is the .xml link for a directory on a THREDDS Data 
        Server.
        '''
        urls = []
        try:
            self.logger.info("Checking for updates at %s", catalog_url)
            req = requests.get(catalog_url)
        except ConnectionError as e:
            self.logger.error('Cannot open catalog_url = %s', catalog_url)
            self.logger.exception(e)
            return urls

        soup = BeautifulSoup(req.text, 'html.parser')

        # Expect that this is a standard TDS with dodsC used for OpenDAP
        base_url = '/'.join(catalog_url.split('/')[:4]) + '/dodsC/'

        # Pull out <dataset ... urlPath='...nc'> attributes from the XML
        for e in soup.findAll('dataset', attrs={'urlpath': re.compile("nc$")}):
            urls.append(base_url + e['urlpath'])

        return self._sort_opendap_urls(urls)

    def _get_cache_file_parms(self, cache_file):
        '''Return dictionary of constraint parameters from name of fixed cache file.
        '''
        parm_dict = {}
        if self._fixed_cache_base in cache_file:
            for regex in [a for a in dir(self) if not callable(a) and 
                                                  a.endswith("RE")]:
                try:
                    p = re.compile(self.__getattribute__(regex))
                    m = p.search(cache_file)
                    parm_dict[regex[1:-2]] = m.group(1)
                except AttributeError:
                    pass

        return parm_dict

    def _validate_cache_file_parm(self, parm, value):
        '''Return adjusted parm value so as not to exceed fixed cache file value.
        '''
        adjusted_value = value
        cache_file_value = None
        try:
            cache_file_value = self.cache_file_parms[parm]
        except KeyError:
            if isinstance(value, int) and not adjusted_value:
                # Return a ridiculously large integer to force reading all data
                adjusted_value =  self._MAX_VALUE
        except AttributeError:
            # No cache_file sepcified
            pass

        if value and cache_file_value:
            if isinstance(value, int):
                if value > cache_file_value:
                    self.logger.warn("Requested %s %s exceeds cache file's parameter: %s",
                                      parm, value, cache_file_value)
                    self.logger.info("Setting %s to %s", parm, cache_file_value)
                    adjusted_value = int(cache_file_value)
            else:
                if not set(value) <= set(cache_file_value.split('-')):
                    self.logger.warn("Requested item(s) %s %s not in fixed cache file: %s",
                                      parm, set(value), cache_file_value)
                    adjusted_value = cache_file_value.split('-')

        elif not value and cache_file_value:
            self.logger.info("Using fixed cache file's %s value of %s", parm, 
                                                            cache_file_value)
            if parm == 'wmo':
                adjusted_value = cache_file_value.split('-')
            else:
                adjusted_value = int(cache_file_value)

        if not adjusted_value:
            # Final check for value = None and not set by cache_file
            if not isinstance(value, (list, tuple)):
                adjusted_value = self._MAX_VALUE

        return adjusted_value

    def _validate_oxygen(self, df, url, var_name='DOXY_ADJUSTED'):
        '''Return blank DataFrame if no valid oxygen otherwise return df.
        '''
        if df[var_name].dropna().empty:
            self.logger.warn('Oxygen is all NaNs in %s', url)
            df = self._blank_df

        return df

    def _save_profile(self, url, count, opendap_urls, wmo, key, code,
                      max_pressure, float_msg, max_profiles):
        '''Put profile data into the local HDF cache.
        '''
        m_t = '{}, Profile {} of {}, key = {}, code = {}'
        m_t_mp = '{}, Profile {} of {}({}), key = {}, code = {}'
        msg = m_t.format(float_msg, count + 1, len(opendap_urls), key, code)
        try:
            if max_profiles != self._MAX_VALUE:
                msg = m_t_mp.format(float_msg, count + 1, len(opendap_urls), 
                                    max_profiles, key, code)
        except NameError:
            pass

        try:
            self.logger.info(msg)
            df = self._profile_to_dataframe(wmo, url, key, max_pressure).dropna()
            if df.empty:
                df = self._blank_df
            else:
                if 'DOXY_ADJUSTED' in self._bio_list:
                    df = self._validate_oxygen(df, url, 'DOXY_ADJUSTED')
                elif 'DOXY' in self._bio_list:
                    df = self._validate_oxygen(df, url, 'DOXY')
        except RequiredVariableNotPresent as e:
            self.logger.warn(str(e))
            df = self._blank_df
        except KeyError as e:
            self.logger.error(str(e))
            df = self._blank_df

        self._put_df(df, key, dict(url=url, dateloaded=datetime.utcnow()))

        return df

    def _get_data_from_argo(self, wmo_list, max_profiles=None, max_pressure=None,
                                  append_df=True, update_delayed_mode=False):
        '''Query Argo web resources for all the profile data for floats in
        wmo_list. Return DataFrame.
        '''
        max_profiles = self._validate_cache_file_parm('profiles', max_profiles)
        max_pressure = self._validate_cache_file_parm('pressure', max_pressure)
        max_wmo_list = self._validate_cache_file_parm('wmo', wmo_list)

        float_df = pd.DataFrame()
        for f, (wmo, dac_url) in enumerate(self.get_dac_urls(max_wmo_list).iteritems()):
            float_msg = 'WMO_{}: Float {} of {}'. format(wmo, f+1, len(max_wmo_list))
            opendap_urls = self.get_profile_opendap_urls(dac_url)
            for i, url in enumerate(opendap_urls):
                if i >= max_profiles:
                    self.logger.info('Stopping at max_profiles = %s', max_profiles)
                    break
                try:
                    key, code = self._float_profile_key(url)
                except AttributeError:
                    continue
                try:
                    df, m = self._get_df(key)
                    self.logger.debug(m['url'])
                    if 'D' in code.upper() and update_delayed_mode:
                        DATE_UPDATED = self._get_update_datetime(url)
                        if DATE_UPDATED:
                            if m['dateloaded'] < DATE_UPDATED:
                                self.logger.info(
                                        'Replacing %s as dateloaded time of %s'
                                        ' is before DATE_UPDATED time of %s',
                                        key, m['dateloaded'], DATE_UPDATED)
                                self._remove_df(key)
                                raise KeyError
                except KeyError:
                    df = self._save_profile(url, i, opendap_urls, wmo, key, code,
                                            max_pressure, float_msg, max_profiles)

                self.logger.debug(df.head())
                if append_df and not df.dropna().empty:
                    float_df = float_df.append(df)

        return float_df

    def _get_data_from_cache(self, wmo_list, wmo_df, max_profiles=None):
        '''Return DataFrame of data in the cache file without querying Argo
        '''
        max_profiles = self._validate_cache_file_parm('profiles', max_profiles)
        # TODO: Make sure all in wmo_list is in max_wmo_list
        ##max_wmo_list = self._validate_cache_file_parm('wmo', wmo_list)

        float_df = pd.DataFrame()
        for f, wmo in enumerate(wmo_list):
            rows = wmo_df.loc[wmo_df['wmo'] == wmo, :]
            for i, (_, row) in enumerate(rows.iterrows()):
                if i >= max_profiles:
                    self.logger.info('%s stopping at max_profiles = %s', wmo, max_profiles)
                    break
                try:
                    key, code = self._float_profile_key(row['url'])
                except AttributeError:
                    continue

                self.logger.debug('Float %s of %s, Profile %s of %s: %s', 
                                 f+1, len(wmo_list), i+1, len(rows), key)
                df, _ = self._get_df(key)
                if not df.dropna().empty:
                    float_df = float_df.append(df)

        return float_df


    def get_float_dataframe(self, wmo_list, max_profiles=None, max_pressure=None,
                                  append_df=True, update_delayed_mode=False,
                                  update_cache=True):
        '''Returns Pandas DataFrame for all the profile data from wmo_list.
        Uses cached data if present, populates cache if not present.  If 
        max_profiles limits the number of profiles returned per float,
        this is useful for testing or for getting just 
        the most recent profiles from the float. To load only surface data
        set a max_pressure value. Set append_df to False if calling simply 
        to load cache_file (reduces memory requirements).  Set update_delayed_mode
        to True to reload into the cache updated delayed mode data.  If
        update_cache is True then each DAC will be queried for new profile
        data, which can take some time; for reading just data from the cache
        set update_cache=False.
        '''
        if update_cache:
            df = self._get_data_from_argo(wmo_list, max_profiles, max_pressure,
                                          append_df, update_delayed_mode)
        else:
            wmo_df = self.get_profile_metadata(flush=False)
            df = self._get_data_from_cache(wmo_list, wmo_df, max_profiles)

        return df

    def _build_profile_metadata_df(self, wmo_dict):
        '''Read metadata from .hdf file to return a DataFrame of the metadata
        for each profile name in wmo_dict.
        '''
        profiles = []
        url_hash = {}
        Profile = namedtuple('profile', 'wmo name url code dateloaded')
        with pd.HDFStore(self.cache_file, mode='r+') as f:
            self.logger.debug('Building wmo_df by scanning %s', self.cache_file)
            for name, wmo in wmo_dict.iteritems():
                m = f.get_storer(name).attrs.metadata
                _, code = self._float_profile_key(m['url'])
                profiles.append(Profile(wmo, name, m['url'], code, m['dateloaded']))
                url_hash[m['url']] = Profile(wmo, name, m['url'], code, m['dateloaded'])

        # Sort profiles in code order: D, MR, and the rest
        sorted_profiles = []
        for url in self._sort_opendap_urls(url_hash.keys()):
            sorted_profiles.append(url_hash[url])

        df = pd.DataFrame.from_records(sorted_profiles, columns=profiles[0]._fields)

        return df

    def get_profile_metadata(self, flush=False):
        '''Return DataFrame of all profile metadata in the cache file
        '''
        if flush:
            try:
                with pd.HDFStore(self.cache_file, mode='r+') as s:
                    s.remove(self._ALL_WMO_DF)
            except KeyError:
                pass
        try:
            with pd.HDFStore(self.cache_file, mode='r+') as s:
                wmo_df = s[self._ALL_WMO_DF]
                self.logger.debug('Read %s from cache', self._ALL_WMO_DF)
        except (KeyError, TypeError):
            self.logger.debug('Building float_dict by scanning %s', self.cache_file)
            with pd.HDFStore(self.cache_file, mode='r+') as f:
                float_dict = {g: g.split('/')[1].split('_')[1]
                              for g in sorted(f.keys()) if g.startswith('/WMO')}

            wmo_df = self._build_profile_metadata_df(float_dict)
            self.logger.info('Putting %s into cache', self._ALL_WMO_DF)
            with pd.HDFStore(self.cache_file, mode='r+') as s:
                s.put(self._ALL_WMO_DF, wmo_df, format='fixed')

        return wmo_df

    def get_cache_file_all_wmo_list(self, flush=False):
        '''Return wmo numbers of all the floats in the cache file.  Has side
        effect of storing DataFrame of all profile urls indexed by wmo number.
        '''
        wmo_df = self.get_profile_metadata(flush)

        return wmo_df['wmo'].unique().tolist()

    def get_cache_file_oxy_count_df(self, max_profiles=None, flush=False):
        '''Return DataFrame of profile and measurment counts for each float
        that contains oxygen data in the cache file.  Limit loading additional 
        profiles by setting max_profiles.
        '''
        oxy_count_df = pd.DataFrame()
        if flush:
            try:
                with pd.HDFStore(self.cache_file, mode='r+') as s:
                    s.remove(self._OXY_COUNT_DF)
            except KeyError:
                pass
        try:
            with pd.HDFStore(self.cache_file, mode='r+') as s:
                oxy_count_df = s[self._OXY_COUNT_DF]
                self.logger.info('Read %s from cache', self._OXY_COUNT_DF)
        except KeyError:
            oxy_hash = {}
            for wmo in self.get_cache_file_all_wmo_list(flush=False):
                self.logger.info('Getting %s from cache', wmo)
                df = self.get_float_dataframe([wmo], max_profiles, update_cache=False)
                try:
                    if not df['DOXY_ADJUSTED'].dropna().empty:
                        odf = df.dropna().xs(wmo, level='wmo')
                        oxy_hash[wmo] = (
                                len(odf.index.get_level_values('time').unique()),
                                len(odf))
                except (KeyError, AttributeError):
                    pass
                try:
                    if not df['DOXY'].dropna().empty:
                        odf = df.dropna().xs(wmo, level='wmo')
                        oxy_hash[wmo] = (
                                len(odf.index.get_level_values('time').unique()),
                                len(odf))
                except (KeyError, AttributeError):
                    pass

            num_profiles = pd.Series([v[0] for v in oxy_hash.values()])
            num_measurements = pd.Series([v[1] for v in oxy_hash.values()])
            oxy_count_df = pd.DataFrame(dict(wmo = pd.Series(oxy_hash.keys()), 
                                    num_profiles = num_profiles, 
                                    num_measurements = num_measurements))

            self.logger.info('Putting %s into cache', self._OXY_COUNT_DF)
            with pd.HDFStore(self.cache_file, mode='r+') as s:
                s.put(self._OXY_COUNT_DF, oxy_count_df, format='fixed')

        return oxy_count_df

