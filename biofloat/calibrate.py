import pandas as pd
import xray

from biofloat.utils import o2sat, convert_to_mll

'''Collection of functions derived from biofloat Notebook 
explore_surface_oxygen_and_WOA.ipynb. 
'''

# Global woa dictionary of urls to the World Ocean Atlas monthly climatology
woa_tmpl = 'http://data.nodc.noaa.gov/thredds/dodsC/woa/WOA13/DATA/o2sat/netcdf/all/1.00/woa13_all_O{:02d}_01.nc'
woa = {}
for m in range(1,13):
    woa[m] = woa_tmpl.format(m)


def round_to(n, increment, mark):
    '''Round n to nearest increment at mark, e.g.:
        In [10]: round_to(36.1, 1, 0.5)
        Out[10]: 36.5
    '''
    correction = mark if n >= 0 else -mark
    return int( n / increment) + correction

def woa_o2sat(month, depth, lon, lat):
    '''Perform the WOA climatology database lookup for the temporal
    spatial corrdinates passed in.
    '''
    ds = xray.open_dataset(woa[month], decode_times=False)

    return ds.loc[dict(lon=lon, lat=lat, depth=depth)]['O_an'].values[0]

def surface_mean(df, max_pressure=10):
    '''Return DataFrame of surface mean values for data with pressure 
    less than max_pressure.
    '''
    return df.query(('pressure < {:d}').format(max_pressure)).groupby(
            level=['wmo', 'time', 'lon', 'lat', 'profile']).mean()

def add_columns_for_groupby(df):
    '''Add columns derived from the index to make groupbys easier.
    '''
    df['lon'] = df.index.get_level_values('lon')
    df['lat'] = df.index.get_level_values('lat')
    df['month'] = df.index.get_level_values('time').month
    df['year'] = df.index.get_level_values('time').year
    df['wmo'] = df.index.get_level_values('wmo')

    return df

def monthly_mean(df):
    '''Return DataFrame of monthly mean of the float data. These columns need
    to be in df: ['wmo', 'year', 'month']
    '''
    mdf = df.groupby(['wmo', 'year', 'month']).mean()
    mdf['o2sat'] = 100 * (mdf.DOXY_ADJUSTED / o2sat(mdf.PSAL_ADJUSTED, mdf.TEMP_ADJUSTED))

    return mdf

def add_columns_for_woa_lookup(df):
    '''Add rounded ilat and ilon columns to facilitate WOA lookup
    '''
    df['ilon'] = df.apply(lambda x: round_to(x.lon, 1, 0.5), axis=1)
    df['ilat'] = df.apply(lambda x: round_to(x.lat, 1, 0.5), axis=1)

    return df

def add_column_from_woa(df, pressure=5.0):
    '''Adds 'woa_o2sat' column to df at provided pressure.
    '''
    df['month'] = df.index.get_level_values('month')
    df['woa_o2sat'] = df.apply(lambda x: woa_o2sat(x.month, pressure, x.ilon, x.ilat), axis=1)

    return df


def calculate_gain(df):
    '''Calculate gain. Add 'wmo' column back and make a Python datetime index as column 'date'. 
    Return a simplified DataFrame with just O2 and gain columns.
    '''
    gdf = df[['o2sat', 'woa_o2sat']].copy()
    gdf['wmo'] = gdf.index.get_level_values('wmo')
    years = gdf.index.get_level_values('year')
    months = gdf.index.get_level_values('month')
    gdf['date'] = pd.to_datetime(years * 100 + months, format='%Y%m')
    gdf['gain'] = gdf.woa_o2sat / gdf.o2sat

    return gdf

