import json
from typing import Dict
import pandas as pd
import time 

with open('config.json','r') as files:
    users = json.load(files)

mandatory_fields = ['Item Exception Flag','Total Lead Time','Exception','Supplier Site','Quantity','Past Due Range'] # ,'main_category','AI_PRIORITY'

exception           = ['Orders to be rescheduled out', 'Past due orders', 'Orders to be cancelled', 'Orders to be rescheduled in', 'Orders with compression days']
item_exception_flag = ['Within Control Limits (Green)', 'Above Max <= $20 K (Yellow)', 'Below Zero (Red)', 'Below SS < 50% of SS (Orange)', 'Below SS > = 50% of SS (Yellow)', 'Above Max $20 K - $50 K (Orange)', 'Above Max > $50 K (Red)']


exception_flag_mapping = { 
                          'Above Max > $50 K (Red)':0.7,
                          'Above Max $20 K - $50 K (Orange)':0.6,
                          'Above Max <= $20 K (Yellow)':0.5,
                          'Below Zero (Red)':0.4,
                          'Below SS < 50% of SS (Orange)':0.3,
                          'Below SS > = 50% of SS (Yellow)':0.2,
                          'Within Control Limits (Green)':0.1
                        }

exception_mapping = {
    "Past due orders": 0.5,
    "Orders with compression days": 0.4,
    "Orders to be rescheduled in": 0.3,
    "Orders to be rescheduled out": 0.2,
    "Orders to be cancelled": 0.1
}

due_mapping = {
    '30+':0.4, 
    '21-30':0.3,
    '11-20':0.2,
    '1-10':0.1,
    '0': 0.0
}

exception_flag_categorical_mapping = {'Within Control Limits (Green)':"category2", 
                                    'Below Zero (Red)':"category2",
                                    'Below SS > = 50% of SS (Yellow)':"category2",
                                    'Below SS < 50% of SS (Orange)':"category2",
                                    'Above Max > $50 K (Red)':"category1",
                                    'Above Max $20 K - $50 K (Orange)':"category1",
                                    'Above Max <= $20 K (Yellow)':"category1"}

main_category = {
    'category1':2,
    'category2':1,
}

selected_columns = ['Item Exception Flag','Total Lead Time','Exception','Supplier Site','Quantity','Past Due Range']

stats_information = {'Total Lead Time':{"Max Value":200,'Min Value':0}, 
                      'Supplier Site':{"Max Value":50000,'Min Value':0}, 
                      'Quantity':{"Max Value":100000,'Min Value':0}, 
                      }


feature_mapping = {'feature_mapping':selected_columns,
                   'exception_flag_mapping':exception_flag_mapping,
                   'exception_mapping':exception_mapping,
                   'due_mapping':due_mapping,
                   'exception_flag_categorical_mapping':exception_flag_categorical_mapping,
                   'main_category':main_category,
                   'stats_information':stats_information,
                   'numerical_feature':['Supplier Site','Quantity','Total Lead Time']
                   }

def get_home_dropdwon_info()->Dict:
    return {
            'filename'                : 'No file selected for AI/ML prediction',
            'planner_name_desc'       : ['Not Found'],
            'exception'               : exception,
            'selected_planner'        : 'Not Found',
            'dataset'                 : pd.DataFrame(columns=['Planner Name Desc','Exception','Item Exception Flag']),
            'item_exception_flag'     : item_exception_flag,
            'balance_exception'       : pd.DataFrame(),
            'balance_exception_flag'  : pd.DataFrame(),
            'columns_info'            : [],
            'records'                 : [],
            'number_of_records'       : 0,
            'high_priority_info'      : {'high_priority':'0','high_priority_info':''},
            'assigned_priority'       : ['Planner','All'],
            'selected_priority'       : 'Planner',
            'number_of_exception'     : 0,
            'predicted_dataset'       : pd.DataFrame()
            }
