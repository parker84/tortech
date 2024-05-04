import streamlit as st
import coloredlogs, logging
import pandas as pd
from collections import Counter
from decouple import config
logger = logging.getLogger(__name__)
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'))

st.set_page_config(
    page_title='TorTech',
    page_icon='🦖',
    layout='wide',
)
st.title('TorTech 🦖 Database')

st.caption('Explore the top Toronto-Based Tech Companies 🇨🇦')


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
df['max_employees_for_sorting'] = [
    int(x.split('-')[-1].replace('k', '000').replace('+', ''))
    for x in df['Employees']
]

employee_options = (
    df[['max_employees_for_sorting', 'Employees']].drop_duplicates()
    .sort_values(by='max_employees_for_sorting', ascending=False)
    ['Employees'].tolist()
)

all_tags = []
for tags in df['Tags']:
    for tag in tags.split(', '):
        all_tags.append(tag)
tag_counts = Counter(all_tags)
tag_options = [
    val[0] for val in
    sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
]

st.sidebar.subheader('⚙️ Filters')

employees = st.sidebar.multiselect(
    'Employees',
    options=['Select All'] + employee_options,
    default=['Select All']
)

tags = st.sidebar.multiselect(
    'Tags',
    options=['Select All'] + tag_options,
    default=['Select All']
)

st.sidebar.caption("Want to say thanks? \n[Buy me a coffee ☕](https://www.buymeacoffee.com/brydon)")

df_filtered = df.copy()

if employees != ['Select All']:
    df_filtered = df_filtered[
        df_filtered['Employees'].isin(employees)
    ]

if tags != ['Select All']:
    for tag in tags:
        if tag != 'Select All':
            df_filtered[f'contains_{tag}'] = df_filtered['Tags'].str.contains(tag)
    df_filtered['contains_tag'] = df_filtered[[
        col for col in df_filtered.columns
        if col.startswith('contains_')
    ]].sum(axis=1)
    df_filtered = df_filtered[
        df_filtered['contains_tag'] == 1
    ]


df_filtered = df_filtered.sort_values(by=['Followers', 'max_employees'], ascending=False)
df_filtered = df_filtered[[
    'Company',
    'Employees',
    'Followers',
    'Tags',
    'LinkedIn',
    'Website',
    'Short Description',
    'Long Description'
]]
df_filtered.index = range(1, df_filtered.shape[0]+1)

if df_filtered.shape[0] > 0:
    st.dataframe(
        df_filtered,
        column_config={
            'Company': st.column_config.TextColumn(
                "Company", width="Small"
            ),
            'Followers': st.column_config.ProgressColumn(
                "Followers",
                format="%.0fk",
                width="medium",
                min_value=0,
                max_value=df_filtered['Followers'].max(),
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
        height=700
    )
else:
    st.error('No Companies That Fit This Criteria')