#!/usr/bin/env python3

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from modules.spec import parse_xml, parse_txt, get_best_slope
import io
import base64

st.set_option('deprecation.showfileUploaderEncoding', False)

def download_csv(df):

    '''convert dataframe to bytes and generate link to download'''

    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="output.csv">Download slope data csv file</a>'

    return href


def set_lin_fit(df, plot_fit_df):

    '''dataframe with linear fit lines'''

    x_range = df['time_s'].unique()

    lin_df_list = []
    for well in df['well_name'].unique():
        subset = plot_fit_df.query("Well == @well")
        slope = subset['Slope'].values[0] / 1000 / 60
        y_int = subset['Y_Int'].values[0]

        ys = slope * x_range + y_int

        lin_df = pd.DataFrame()
        lin_df['y'] = ys
        lin_df['x'] = x_range
        lin_df['fit'] = f'{well} fit'
        lin_df['well_name'] = well
        lin_df_list.append(lin_df)

    lin_df = pd.concat(lin_df_list, ignore_index=True)

    return lin_df


def plot_traces(df, x_start, x_end, plot_fit_df=None):

    '''plot absorbance traces vs time'''

    # human sort legend labels
    uniq_wells = df['well_name'].unique()
    wells_sorted = sorted(uniq_wells, key=lambda x: (x[0], int(x[1:])))

    # interactive legend
    selection = alt.selection_multi(fields=['well_name'], bind='legend')

    # draw endpoints
    start = alt.Chart(pd.DataFrame({'start' : [x_start]})).mark_rule(size=2).encode(x='start')
    end = alt.Chart(pd.DataFrame({'end' : [x_end]})).mark_rule(size=2).encode(x='end')

    # plot linear fit
    if plot_fit_df is not None:
        lin_df = set_lin_fit(df, plot_fit_df)

        # linear
        line2 = alt.Chart(lin_df).mark_line(size=3).encode(
            x = alt.X('x'),
            y = alt.Y('y'),
            color=alt.Color('well_name', sort=wells_sorted, legend=alt.Legend(title='Well')),
            opacity = alt.condition(selection, alt.value(1), alt.value(0.2))
        ).add_selection(selection)

        # raw
        line = alt.Chart(df).mark_line().encode(
            x=alt.X('time_s:Q', axis=alt.Axis(title='Time (s)')),
            y=alt.Y('reads:Q', axis=alt.Axis(title='Absorbance')),
            color= alt.Color('well_name', legend=None, sort=wells_sorted),
            opacity = alt.value(0.2))

        plots = [line, line2, start, end]

    else:

        # raw only
        line = alt.Chart(df).mark_line().encode(
            x=alt.X('time_s:Q', axis=alt.Axis(title='Time (s)')),
            y=alt.Y('reads:Q', axis=alt.Axis(title='Absorbance')),
            color=alt.Color('well_name', sort=wells_sorted, legend=alt.Legend(title='Well')),
            opacity = alt.condition(selection, alt.value(1), alt.value(0.2))
        ).add_selection(selection)

        plots = [line, start, end]

    p = alt.layer(*plots).properties(
            width = 750,
            height = 500
        ).configure_axis(labelFontSize=12, gridOpacity=0.4, titleFontSize=15,
        ).configure_legend(labelFontSize=13, titleFontSize=15,
        ).interactive()

    return p

def get_slopes(df, x_start, x_end, span):

    '''get max abs slopes'''

    # get slopes
    slope_dfs = []
    for well in df_selected['well_name'].unique():
        slope_df = get_best_slope(df, well, x_start, x_end, span)
        slope_df['well'] = well
        slope_dfs.append(slope_df)

    slope_df = pd.concat(slope_dfs, ignore_index=True)
    slope_df.columns = [col.title() for col in slope_df.columns.values]
    slope_df.index = slope_df.index + 1

    return slope_df

if __name__ == '__main__':

    st.title('Spectramax Dashboard')

    st.sidebar.markdown('# Options')

    # upload spectramax xml output
    file_buffer = st.file_uploader('Upload Spectramax output (xml or txt columns)', type=['xml', 'txt'])
    if file_buffer:
        text_io = io.TextIOWrapper(file_buffer, encoding='utf-16').read()

        # check file format
        # text columns
        if text_io.startswith('##BLOCKS'):
            df = parse_txt(text_io)

        # xml format
        else:
            df = parse_xml(text_io)

        print(df)

        # add sidebar elements
        step = df['time_s'].values[1]
        end = df['time_s'].values[-1]
        samples = list(df['well_name'].unique())

        plot_fit = st.sidebar.checkbox('Plot linear fit')
        x_start = st.sidebar.number_input('Start time', min_value=0, value=0, step=step)
        x_end = st.sidebar.number_input('End time', max_value=end, value=end, step=step)

        max_span = (x_end - x_start) // step + 1
        span = st.sidebar.number_input('Span', min_value=2, value=max_span, max_value=max_span)
        selected = st.sidebar.multiselect('Selected samples', options=samples, default=samples)

        # plot traces with selected sample
        df_selected = df.query("well_name in @selected")

        # slopes
        slope_df = get_slopes(df_selected, x_start, x_end, span)
        slope_df_disp = slope_df[['Well', 'Slope', 'R2', 'Start', 'End']]

        # plot linear fit, will have already calculated slopes once
        if plot_fit:
            p = plot_traces(df_selected, x_start, x_end, slope_df)
        else:
            p = plot_traces(df_selected, x_start, x_end)

        st.write(p)
        st.table(slope_df_disp.style.format({'Slope': '{:.3f}',
                                             'R2' : '{:.3f}'}))
        st.markdown(download_csv(slope_df_disp), unsafe_allow_html=True)
