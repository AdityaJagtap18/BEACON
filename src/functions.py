import os
import io
import base64
import pandas as pd
import numpy as np
import pickle
import plotly.express as px
import plotly.io as pio
from plotly import graph_objects as go
import json
import logging
import warnings
warnings.filterwarnings("ignore")
exception_mapping = {
    'Orders to be rescheduled out':'rescheduled out', 
    'Past due orders':'past due',
    'Orders to be cancelled':'cancelled', 
    'Orders to be rescheduled in':'rescheduled in', 
    'Orders with compression days':'compression'
}

def create_log_files(user_name):

    # Define logger name per user
    logger = logging.getLogger(user_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler for each user logs\admin.log
        file_handler = logging.FileHandler(f"logs\{user_name}.log")
        file_handler.setLevel(logging.INFO)

        # Log format
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger

def load_user_info(file_path=r'json\user_config.json'):
    with open(file_path, 'r') as files:
        knowledge_info = json.load(files)
        return knowledge_info

item_exception_mapping = {'Within Control Limits (Green)':'Control Limits',
                          'Above Max <= $20 K (Yellow)':'Above Max <= $20K', 
                          'Below Zero (Red)':'Below Zero', 
                          'Below SS < 50% of SS (Orange)':'Below SS<50% of SS', 
                          'Below SS > = 50% of SS (Yellow)':'Below SS>= 50% of SS', 
                          'Above Max $20 K - $50 K (Orange)':'Above Max $20K-$50 K', 
                          'Above Max > $50 K (Red)':'Above Max>$50K'}

item_exception_color_mapping = {'Within Control Limits (Green)':'Green',
                                'Above Max <= $20 K (Yellow)':'Yellow', 
                                'Below Zero (Red)':'Red', 
                                'Below SS < 50% of SS (Orange)':'Orange', 
                                'Below SS > = 50% of SS (Yellow)':'Yellow', 
                                'Above Max $20 K - $50 K (Orange)':'Orange', 
                                'Above Max > $50 K (Red)':'Red'}

def get_dummy_info(table_info,metadata,cols):
    selected_cols = table_info.columns[1]

    if table_info.shape[0]==0:
        dummy_info = pd.DataFrame([['Not Found',row,0] for row in metadata[cols]],columns=table_info.columns)
        
        merge_info = dummy_info

    if table_info.shape[0]!=0:
        unique_cols = [row for row in metadata[cols] if row not in table_info[selected_cols].unique()]
        dummy_info  = pd.DataFrame([[metadata['selected_planner'],row,0] for row in unique_cols],columns=table_info.columns)
        merge_info = pd.concat([table_info,dummy_info])
    
    return merge_info
        
def get_aggregated_info_all(metadata):
    if metadata['dataset'].shape[0]!=0:
       dataset           = metadata['dataset'][~metadata['dataset']['Planner Name Desc'].isnull()]

    if metadata['dataset'].shape[0]==0:
       dataset           = metadata['dataset']

    # common_information   = dataset[(dataset['Item Exception Flag']=='Above Max > $50 K (Red)') |
    #                                (dataset['Item Exception Flag']=='Below Zero (Red)')]
    
    exception_stat_info       = dataset.groupby(['Exception'])['Exception'].agg(['count']).reset_index()
    exception_stat_info.rename(columns={"count":'Freq'},inplace=True)
    exception_stat_info['Planner Name Desc'] = 'All'

    exception_stat_info['Exception Upg'] = exception_stat_info['Exception'].map(exception_mapping)
    
    item_exception_stat_info  = dataset.groupby(['Item Exception Flag'])['Item Exception Flag'].agg(['count']).reset_index()
    item_exception_stat_info.rename(columns={"count":'Freq'},inplace=True)
    item_exception_stat_info['Item Exception Flag Upg'] = item_exception_stat_info['Item Exception Flag'].map(item_exception_mapping)
    item_exception_stat_info['Flag']                    = item_exception_stat_info['Item Exception Flag'].map(item_exception_color_mapping)
    item_exception_stat_info['Planner Name Desc']       = 'All'
    return {"balance_exception":exception_stat_info,
            "balance_exception_flag":item_exception_stat_info}

def get_aggregated_info(metadata):
    if metadata['dataset'].shape[0]!=0:
       dataset           = metadata['dataset'][~metadata['dataset']['Planner Name Desc'].isnull()]

    if metadata['dataset'].shape[0]==0:
       dataset           = metadata['dataset']
    
    exception_info      = metadata['exception']
    item_exception_flag = metadata['item_exception_flag']
    selected_planner    = metadata['selected_planner']

    planner_agg_info  = dataset[dataset['Planner Name Desc']==selected_planner].groupby(['Planner Name Desc','Exception'])['Exception'].agg(['count']).reset_index()
    planner_agg_info.rename(columns={"count":'Freq'},inplace=True)

    exception_agg_info = dataset[dataset['Planner Name Desc']==selected_planner].groupby(['Planner Name Desc','Item Exception Flag'])['Item Exception Flag'].agg(['count']).reset_index()
    exception_agg_info.rename(columns={"count":'Freq'},inplace=True)
    
    balance_exception = get_dummy_info(table_info  = planner_agg_info,
                                       metadata    = metadata,
                                       cols        = 'exception')

    balance_exception['Exception Upg'] = balance_exception['Exception'].map(exception_mapping)
    balance_exception_flag = get_dummy_info(table_info  = exception_agg_info,
                                       metadata    = metadata,
                                       cols        = 'item_exception_flag')
    
    balance_exception_flag['Item Exception Flag Upg'] = balance_exception_flag['Item Exception Flag'].map(item_exception_mapping)
    balance_exception_flag['Flag']                    = balance_exception_flag['Item Exception Flag'].map(item_exception_color_mapping)
    
    # print(planner_agg_info)
    # print(exception_agg_info)
    return {"balance_exception":balance_exception,
            "balance_exception_flag":balance_exception_flag}


def bar_plot(information,type_plot):
    fig = go.Figure()
    fig.update_layout(yaxis_title=None)
    fig.update_layout(xaxis_title=None)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=4, r=4, b=10, t=30, pad=1),
        title="",
        template="plotly_white",
        font=dict(size=9),
        legend_title_text=None,
    )
    if information.shape[0]!=0:

        if type_plot =='Exception': 
            fig.add_trace(
                go.Bar(
                    x=information['Exception Upg'],
                    y=information["Freq"],
                    orientation='v',
                    name="Exception",

                    text=information[['Exception','Planner Name Desc',"Freq"]].apply(
                        lambda row: f"Exception: {row['Exception']}<br>Planner Name: {row['Planner Name Desc']}<br>Freq:{row['Freq']}",
                        axis=1,
                    ),
                    hoverinfo="text",
                    # marker=dict(
                    #     color=information.get('volume_info')['nature'].map({'Buy': 'green', 'Sell': 'red'}),  # Assign colors manually
                    # ),
                )
            )

            fig.update_layout(yaxis_title='Exception count')
            #fig.update_layout(xaxis_title='Exception')
            fig.update_layout(
                showlegend=False,
                margin=dict(l=4, r=4, b=10, t=30, pad=1),
                title="",
                template="plotly_white",
                font=dict(size=8),
                legend_title_text=None,
            )

        if type_plot =='Item Exception Flag': 
            fig.add_trace(
                go.Bar(
                    x=information['Item Exception Flag Upg'],
                    y=information["Freq"],
                    orientation='v',
                    name="Item Exception Flag",

                    text=information[['Item Exception Flag','Planner Name Desc',"Freq"]].apply(
                        lambda row: f"Exception Flag: {row['Item Exception Flag']}<br>Planner Name: {row['Planner Name Desc']}<br>Freq:{row['Freq']}",
                        axis=1,
                    ),
                    hoverinfo="text",
                    # marker=dict(
                    #     color=information.get('volume_info')['nature'].map({'Buy': 'green', 'Sell': 'red'}),  # Assign colors manually
                    # ),
                )
            )

            fig.update_layout(yaxis_title='Exception Flag count')
            #fig.update_layout(xaxis_title='Exception Flag')
            fig.update_layout(
                showlegend=False,
                margin=dict(l=4, r=4, b=10, t=30, pad=1),
                title="",
                template="plotly_white",
                font=dict(size=8),
                legend_title_text=None,
            )

    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="right", x=0.9)
    )  
    
    return fig

def data_preperation(df, feature_mapping):
    selected_columns  = feature_mapping.get('feature_mapping')
    filter_info       = df[selected_columns]
    filter_info['Id'] = np.arange(0,filter_info.shape[0])
    filter_info       = filter_info.set_index('Id')

    # Data Transformations
    filter_info['main_category']  = filter_info['Item Exception Flag'].map(feature_mapping.get('exception_flag_categorical_mapping'))
    filter_info['Past Due Range'] = filter_info['Past Due Range'].astype(str)

    # Filling Missing Values
    cols_to_scale = feature_mapping.get('numerical_feature') 
    #['Supplier Site','Quantity','Total Lead Time']
    for columns in cols_to_scale:
        filter_info[columns].fillna(filter_info[columns].mean(),inplace=True)

    # Converting Categorical Feature into Numerical
    # filter_info['Stratify']            = filter_info['Item Exception Flag'] + filter_info['main_category']
    filter_info['Item Exception Flag'] = filter_info['Item Exception Flag'].map(feature_mapping.get('exception_flag_mapping'))
    filter_info['Exception']           = filter_info['Exception'].map(feature_mapping.get('exception_mapping'))
    filter_info['Past Due Range']      = filter_info['Past Due Range'].map(feature_mapping.get('due_mapping'))
    filter_info['main_category']       = filter_info['main_category'].map(feature_mapping.get('main_category'))

    return filter_info

def MinMaxScaler(df,columns,stats_information):
    X_max = stats_information.get(columns).get("Max Value")
    X_min = stats_information.get(columns).get("Min Value")

    # X_scaled = (X - X_min) / (X_max - X_min)

    X_scaled   = np.array([(X - X_min) / (X_max - X_min) for X in df[columns].astype(float).values])

    return X_scaled

def data_normalization(df,feature_mapping):
    feature_sequence = ['Item Exception Flag', 'Total Lead Time', 'Exception', 'Supplier Site',      
                        'Quantity', 'Past Due Range',  'main_category']
    
    for cols in feature_mapping.get('numerical_feature'):
        df[cols] = MinMaxScaler(df,
                                columns           = cols,
                                stats_information = feature_mapping.get('stats_information'))
        
    return df[feature_sequence]

def predictions(df,feature_mapping,loaded_model):
    # Load model back from pickle  
    prepered_info = data_preperation(df, feature_mapping)

    normalized_info = data_normalization(prepered_info, feature_mapping)
    
    # print(normalized_info)
    # Test prediction
    y_pred = loaded_model.predict(normalized_info)
    
    outcome = pd.DataFrame(y_pred,columns=['AI_PRIORTY'])
    outcome['Id'] = normalized_info.index
    outcome['Category'] = normalized_info.main_category

    dy = df
    dy['Id'] = np.arange(0,dy.shape[0])

    mergeset = pd.merge(outcome[['AI_PRIORTY','Category','Id']], dy,
                        left_on = ['Id'], right_on=['Id'], how='left'
                        )
    first_columns = ['AI_PRIORTY','Category','Item Exception Flag', 'Total Lead Time', 'Exception', 'Supplier Site',      
                        'Quantity', 'Past Due Range']
    
    second_columns = [cols for cols in dy.columns if cols not in first_columns]

    final_cols  = first_columns + second_columns

    predicted_results = mergeset[final_cols]

    predicted_results = predicted_results.sort_values(['Category','AI_PRIORTY'],ascending=[False,True])

    predicted_results['AI_PRIORTY'] = predicted_results['AI_PRIORTY'].apply(lambda info: round(info,3))
    return predicted_results