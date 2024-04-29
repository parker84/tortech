import streamlit as st
import coloredlogs, logging
import pandas as pd
from decouple import config
logger = logging.getLogger(__name__)
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'))

st.set_page_config(
    page_title='TorTech',
    page_icon='🦖',
    layout='wide',
    initial_sidebar_state='collapsed'
)

st.title('🦖 TorTech')

st.caption('This database is home to the top Toronto-Based Tech Companies 🇨🇦')


df = pd.read_csv('./data/tortech_database.csv').rename(
    columns={
        'LinkedIn URL': 'LinkedIn',
        'Company URL': 'Website'
    }
)
df['Followers'] = df['Followers'].str.replace('k', '').astype(float)
df['max_employees'] = [
    int(x.split('-')[-1].replace('k', '').replace('+', ''))
    for x in df['Employees']
]
df = df.sort_values(by=['Followers', 'max_employees'], ascending=False)
df = df[[
    'Company',
    'Employees',
    'Followers',
    'Tags',
    'LinkedIn',
    'Website',
    'Short Description',
    'Long Description'
]]
df.index = range(1, df.shape[0]+1)

st.dataframe(
    df,
    column_config={
        'Company': st.column_config.TextColumn(
            "Company", width="Small"
        ),
        'Followers': st.column_config.ProgressColumn(
            "Followers",
            format="%.0fk",
            width="medium",
            min_value=0,
            max_value=df['Followers'].max(),
        ),
        'LinkedIn': st.column_config.LinkColumn(
            "LinkedIn",
            display_text="https://linkedin.com/company/(.*?)/"
        ),
        "Website": st.column_config.LinkColumn(
            "Website",
            display_text="https://(.*?)/"
        )
    },
    height=650
)