# -*- coding: utf-8 -*-
# Module containing functions for converting biofloat DataFrames to other formats

from collections import OrderedDict

def to_odv(df, odv_file_name, vars=None):
    '''Output biofloat DataFrame in Ocean Data View spreadsheet format to
    file named odv_file_name. Pass in a OrderedDict named vars to override
    the default variable list of TEMP_ADJUSTED, PSAL_ADJUSTED, DOXY_ADJUSTED.
    '''
    fixed_bot_depth = 4000.0
    if not vars:
        vars = OrderedDict([
                            ('TEMP_ADJUSTED', 'degree_Celsius'),
                            ('PSAL_ADJUSTED', 'psu'),
                            ('DOXY_ADJUSTED', 'micromole/kg'),
                          ])

    header_base = ('Cruise\tStation\tType\tmon/day/yr\thh:mm\t'
                   'Lon (degrees_east)\t' 'Lat (degrees_north)\t'
                   'Bot. Depth [m]\tDEPTH [m]\tQF\t')

    header_vars = '\t'.join([('{} [{}]\tQF').format(v, u) 
                             for v, u in vars.iteritems()])

    fmt_base = '{}\t' * 10

    header = header_base + header_vars + '\n'

    with open(odv_file_name, 'w') as odv:
        odv.write(header)
        for i, r in df.iterrows():
            rec_base = [i[0], i[4], 'C', i[1].strftime('%m/%d/%Y'), 
                        i[1].strftime('%H:%M'), i[2], i[3], fixed_bot_depth, 
                        i[5], 0]
            rec_vars = '\t'.join([('{:f}\t0').format(r[v]) 
                                  for v in vars.keys()])
            odv.write(fmt_base.format(*rec_base) + rec_vars + '\n')

