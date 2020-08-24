#!/usr/bin/env python3

import pandas as pd 
import numpy as np
from sklearn.linear_model import LinearRegression
from bs4 import BeautifulSoup


# def time_to_sec(time_str):

#     '''convert mm:ss to seconds'''

#     mins = int(time_str.split(':')[0])
#     secs = int(time_str.split(':')[1])

#     return mins * 60 + secs


def parse_xml(xml_str):

    '''parse spectramax xml kinetic reads'''

    soup = BeautifulSoup(xml_str, 'lxml')

    # time interval
    #interval = soup.find('kineticinterval').text
    #interval = time_to_sec(interval)

    # temp data
    temps = soup.find('temperaturedata').text.split()

    # abs data
    wells = soup.find_all('well')
    df_list = []
    for well in wells:

        well_name = well['name']
        well_id = well['wellid']
        reads = well.rawdata.text.split()
        time = well.timedata.text.split()

        df = pd.DataFrame(reads, columns=['reads'])
        df['well_name'] = well_name
        df['well_id'] = well_id
        df['time_s'] = time
        df['temp'] = temps
        #df['time_s'] = range(0, len(df) * interval, interval)

        df_list.append(df)

    df = pd.concat(df_list, ignore_index=True)
    df = df.apply(pd.to_numeric, errors='ignore')

    return df


def get_best_slope(df, well, start, end, span):

    '''calculate interval span with largest absolute slope between start and end'''

    subset = df.query("time_s >= @start & time_s <= @end and well_name == @well")
    chunk_dfs = [subset[i:i+span] for i in range(0, subset.shape[0], span)]

    lr = LinearRegression()

    data = []
    for chunk_df in chunk_dfs:

        if len(chunk_df) != span:
            break
        
        x = chunk_df['time_s'].values.reshape(-1, 1)
        y = chunk_df['reads'].values.reshape(-1, 1)
        lr.fit(x, y)

        # convert from abs/sec to mAbs/min
        slope = lr.coef_[0][0] * 60 * 1000
        r2 = lr.score(x, y)
        y_int = lr.intercept_[0]

        data.append([x[0][0], x[-1][0], slope, r2, y_int])

    df = pd.DataFrame(data, columns=['start', 'end', 'slope', 'r2', 'y_int'])
    df['abs_slope'] = np.absolute(df['slope'])
    df = df.sort_values(by='abs_slope', ascending=False)
    df = df.drop('abs_slope', axis=1)

    return df.head(1)


def parse_txt(txt_path):

    pass
