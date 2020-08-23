#!/usr/bin/env python3

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from modules.spec import parse_xml, get_best_slope
import io

st.set_option('deprecation.showfileUploaderEncoding', False)

def plot_traces(df):
    
    '''plot absorbance traces vs time'''

    # human sort legend labels
    uniq_wells = df['well_name'].unique()
    wells_sorted = sorted(uniq_wells, key=lambda x: (x[0], int(x[1:])))

    # interactive legend
    selection = alt.selection_multi(fields=['well_name'], bind='legend')

    p = alt.Chart(df).mark_line().encode(
            x=alt.X('time_s:Q', axis=alt.Axis(title='Time (s)')),
            y=alt.Y('reads:Q', axis=alt.Axis(title='Absorbance')),
            color=alt.Color('well_name', sort=wells_sorted, legend=alt.Legend(title='Well')),
            opacity = alt.condition(selection, alt.value(1), alt.value(0.2))
        ).add_selection(selection
        ).properties(
            width = 750, 
            height = 500
        ).configure_axis(labelFontSize=12, gridOpacity=0.4, titleFontSize=15,
        ).configure_legend(labelFontSize=13, titleFontSize=15,
        ).interactive()

    return p


if __name__ == '__main__':

    st.title('Spectramax Dashboard')

    st.sidebar.markdown('# Options')
    plot_fit = st.sidebar.checkbox('Plot linear fit')

    # upload spectramax xml output
    file_buffer = st.file_uploader('Upload Spectramax xml', type='xml')
    if file_buffer:
        text_io = io.TextIOWrapper(file_buffer, encoding='utf-16').read()

        # to df
        df = parse_xml(text_io)

        # plot traces
        p = plot_traces(df)
        st.write(p)

        # get slopes
        slope_dfs = []
        for well in df['well_name'].unique():
            slope_df = get_best_slope(df, well, 0, 100, 10)
            slope_df['well'] = well
            slope_dfs.append(slope_df)

        slope_df = pd.concat(slope_dfs, ignore_index=True)
        slope_df.columns = [col.title() for col in slope_df.columns.values]
        slope_df.index = slope_df.index + 1
        st.table(slope_df[['Well', 'Slope', 'R2', 'Start', 'End']].style.format({'Slope': '{:.3f}',
                                                                                     'R2' : '{:.3f}'}))
