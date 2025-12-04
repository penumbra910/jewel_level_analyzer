"""
文件处理工具函数
"""
import pandas as pd
import numpy as np
from datetime import datetime
import io
from typing import Dict, Tuple


def read_uploaded_files(uploaded_file_raw, uploaded_file_conf) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    读取上传的文件
    """
    try:
        # 读取原始数据
        df_raw = pd.read_excel(uploaded_file_raw)
        
        # 读取配置文件（包含两个sheet）
        df_level_conf = pd.read_excel(uploaded_file_conf, sheet_name='level_conf')
        df_level_group = pd.read_excel(uploaded_file_conf, sheet_name='level_group')
        
        return df_raw, df_level_conf, df_level_group
        
    except Exception as e:
        raise ValueError(f"读取文件失败: {str(e)}")


def validate_dataframes(df_raw: pd.DataFrame, 
                       df_level_conf: pd.DataFrame, 
                       df_level_group: pd.DataFrame) -> Dict:
    """
    验证数据完整性
    """
    validation_results = {
        'df_raw_valid': False,
        'df_level_conf_valid': False,
        'df_level_group_valid': False,
        'required_columns': {},
        'missing_columns': {}
    }
    
    # 检查df_raw的必需列
    df_raw_required = ['event_id', 'ap_config_version', 'lv_id', 
                      'total_churn_rate', 'in_level_churn_rate',
                      'avg_start_times', 'rv_efficiency']
    missing_raw = [col for col in df_raw_required if col not in df_raw.columns]
    validation_results['df_raw_valid'] = len(missing_raw) == 0
    validation_results['required_columns']['df_raw'] = df_raw_required
    validation_results['missing_columns']['df_raw'] = missing_raw
    
    # 检查df_level_conf的必需列
    level_conf_required = ['level_name', 'target']
    missing_conf = [col for col in level_conf_required if col not in df_level_conf.columns]
    validation_results['df_level_conf_valid'] = len(missing_conf) == 0
    validation_results['required_columns']['df_level_conf'] = level_conf_required
    validation_results['missing_columns']['df_level_conf'] = missing_conf
    
    # 检查df_level_group的必需列
    level_group_required = ['event_id', 'ap_config_version', 'level_name_list', 'hidden_level_list']
    missing_group = [col for col in level_group_required if col not in df_level_group.columns]
    validation_results['df_level_group_valid'] = len(missing_group) == 0
    validation_results['required_columns']['df_level_group'] = level_group_required
    validation_results['missing_columns']['df_level_group'] = missing_group
    
    return validation_results


def generate_excel_output(df_level_conf: pd.DataFrame, 
                         df_level_group: pd.DataFrame) -> bytes:
    """
    生成Excel输出文件
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_level_conf.to_excel(writer, sheet_name='level_conf', index=False)
        df_level_group.to_excel(writer, sheet_name='level_group', index=False)
    
    return output.getvalue()


def generate_filename() -> str:
    """
    生成输出文件名
    """
    current_time = datetime.now().strftime('%Y%m%d_%H%M')
    return f'Events&Level_upload_{current_time}.xlsx'