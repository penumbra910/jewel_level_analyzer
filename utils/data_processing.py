"""
数据处理核心函数
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set

# 全局常量定义
FUUU_NEW = [
    -1,-5,-1,-3,1,-1,1,-1,3,-1,-1,0,3,-1,-1,3,-1,0,-2,6,-1,3,-1,0,6,-1,-1,3,-1,1,7,-1,-1,2,3,-1,6,0,-1,3,-1,8,-1,-1,3,2,-1,2,9,2,4,-1,3,-2,8,-1,7,-1,1,10,-1,-1,0,-1,3,-1,0,-1,6,-1,-1,-1,0,-1,4,-1,0,-1,7,-1,-1,-1,0,-1,5,-1,0,-1,8,-1,-1,-1,2,-1,6,-1,2,-1,9,-1,-1,-1,2,-1,7,-1,2,-1,9,-1,-1,-1,2,-1,8,-1,2,-1,10,6
]

FUUU_OLD = [
    -6, -5, -1, -3, 1, -1, 1, -1, 3, -1, -1, 0, 3, -1, -1, 3, -1, 0, -2, 6, -1, 3, -1, 0, 6, -1, -1, 3, -1, 1, 7, -1, -1, 2, 3, -1, 6, 0, -1, 3, -1, 8, -1, -1, 3, 2, -1, 2, 9, 2, -1, 3, -1, 8, -1, 2, 7, 1, 2, 10, -1, -1, 0, -1, 3, -1, 0, -1, 6, -1, -1, -1, 0, -1, 3, -1, 0, -1, 6, -1, -1, -1, 0, -1, 3, -1, 0, -1, 6, -1, -1, -1, 2, -1, 5, -1, 2, -1, 6, -1, -1, -1, 2, -1, 5, -1, 2, -1, 6, -1, -1, -1, 2, -1, 5, -1, 2, -1, 6, 5
]

FUUU_EVA = {
    -10: 1, -9: 1, -8: 1, -7: 1, -6: 1, -5: 1, -4: 1,
    -3: 2, -2: 2, -1: 2,
    0: 3, 1: 3, 2: 3,
    3: 4, 4: 4, 5: 4,
    6: 5, 7: 5, 8: 5, 9: 5, 10: 5
}

ATTRIBUTE_MAP = {
    101: "gem", 102: "gem", 103: "gem", 104: "gem",
    4: "stone", 5: "ice", 1: "bomb", 15: "weaponbox",
    17: "verticalroman", 9: "rocket", 7: "rubylaser",
    10: "cassetteplayer", 11: "volcano", 12: "botpole",
    13: "heatingcoil", 14: "fossil", 16: "aquarium",
    18: "lightsabercase", 19: "miningmachine"
}


def create_lookup_dict(df_level_group: pd.DataFrame) -> Dict:
    """
    创建level_name查找字典
    """
    lookup_dict = {}
    
    for _, row in df_level_group.iterrows():
        key = (str(row['event_id']), str(row['ap_config_version']))
        level_name_dict = {}
        
        # 处理level_name_list
        if pd.notna(row['level_name_list']):
            level_list = [item.strip() for item in str(row['level_name_list']).split(',')]
            for i, name in enumerate(level_list, 1):
                level_name_dict[i] = name
        
        # 处理hidden_level_list
        if pd.notna(row['hidden_level_list']):
            hidden_list = [item.strip() for item in str(row['hidden_level_list']).split(',')]
            for i, name in enumerate(hidden_list, 61):
                level_name_dict[i] = name
        
        lookup_dict[key] = level_name_dict
    
    return lookup_dict


def add_level_name(df: pd.DataFrame, df_level_group: pd.DataFrame) -> pd.DataFrame:
    """
    添加level_name列
    """
    df = df.copy()
    df['lv_id'] = df['lv_id'].astype(int)
    
    lookup_dict = create_lookup_dict(df_level_group)
    
    def fast_lookup(row):
        key = (str(row['event_id']), str(row['ap_config_version']))
        return lookup_dict.get(key, {}).get(int(row['lv_id']))
    
    df['level_name'] = df.apply(fast_lookup, axis=1)
    return df


def add_churn_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加churn_rate列
    """
    df = df.copy()
    df['churn_rate'] = df['total_churn_rate'].fillna(df['in_level_churn_rate'])
    return df


def calculate_rev(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算rev列
    """
    df = df.copy()
    df['rev'] = df['avg_start_times'] * 10 + df['rv_efficiency'] * 15
    return df


def add_actual_rev(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算actual_rev列
    """
    df = df.copy()
    
    # 根据lv_id创建分组
    bins = [0, 20, 40, 60, 120]
    labels = ['1-20', '21-40', '41-60', '61-120']
    df['lv_group'] = pd.cut(df['lv_id'], bins=bins, labels=labels, right=True)
    
    # 计算分组平均值
    df['group_avg_rev'] = df.groupby('lv_group', observed=False)['rev'].transform('mean')
    df['group_avg_churn_rate'] = df.groupby('lv_group', observed=False)['churn_rate'].transform('mean')
    
    # 计算actual_rev
    with np.errstate(divide='ignore', invalid='ignore'):
        df['actual_rev'] = df['rev'] - df['churn_rate'] * (df['group_avg_rev'] / df['group_avg_churn_rate'])
        df['actual_rev'] = np.where(df['group_avg_churn_rate'] == 0, df['rev'], df['actual_rev'])
    
    # 删除临时列
    df = df.drop(['lv_group', 'group_avg_rev', 'group_avg_churn_rate'], axis=1)
    
    # 处理异常值
    df.loc[(df['actual_rev'] > 200) | (df['actual_rev'] < -200), 'actual_rev'] = np.nan
    
    return df


def add_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算z-score列
    """
    df = df.copy()
    
    # 筛选event_id >= 60的数据用于计算统计量
    filtered_df = df[df['event_id'] >= 60]
    
    # 计算每个lv_id的统计量
    group_stats = filtered_df.groupby('lv_id')['actual_rev'].agg(['mean', 'std']).reset_index()
    group_stats.columns = ['lv_id', 'mean_actual_rev', 'std_actual_rev']
    
    # 合并回原数据
    df = pd.merge(df, group_stats, on='lv_id', how='left')
    
    # 计算z-score
    with np.errstate(divide='ignore', invalid='ignore'):
        df['z-score'] = (df['actual_rev'] - df['mean_actual_rev']) / df['std_actual_rev']
        df['z-score'] = np.where(df['std_actual_rev'] == 0, 0, df['z-score'])
    
    # 删除临时列
    df = df.drop(['mean_actual_rev', 'std_actual_rev'], axis=1)
    
    return df


def add_fuuu(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加fuuu列
    """
    df = df.copy()
    
    def get_fuuu_value(row):
        lv_id = int(row['lv_id'])
        
        if row['event_id'] < 86:
            # 使用fuuu_old
            if 0 <= (lv_id - 1) < len(FUUU_OLD):
                return FUUU_OLD[lv_id - 1]
        else:
            # 使用fuuu_new
            if 0 <= (lv_id - 1) < len(FUUU_NEW):
                return FUUU_NEW[lv_id - 1]
        
        return None
    
    df['fuuu'] = df.apply(get_fuuu_value, axis=1)
    return df


def add_evaluation(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加evaluation列
    """
    df = df.copy()
    
    def assign_evaluation(row):
        # 只处理event_id >= 60的行
        if row['event_id'] < 60:
            return None
        
        fuuu_value = row['fuuu']
        z_score = row['z-score']
        
        # 检查条件
        if pd.isna(z_score) or pd.isna(fuuu_value):
            return None
        
        try:
            fuuu_int = int(fuuu_value)
        except (ValueError, TypeError):
            return None
        
        # z-score > 1 的情况
        if z_score > 1:
            return FUUU_EVA.get(fuuu_int)
        
        # z-score < -1 的情况
        elif z_score < -1:
            eva_value = FUUU_EVA.get(fuuu_int)
            if eva_value is not None:
                return -eva_value
        
        return None
    
    df['evaluation'] = df.apply(assign_evaluation, axis=1)
    df['evaluation'] = pd.to_numeric(df['evaluation'], errors='coerce').astype('Int64')
    
    return df


def process_attribute(df_level_conf: pd.DataFrame) -> pd.DataFrame:
    """
    处理attribute列
    """
    df_level_conf = df_level_conf.copy()
    
    def parse_target_attributes(target_str):
        if pd.isna(target_str):
            return ""
        
        groups = str(target_str).split(';')
        attributes_set = set()
        
        for group in groups:
            if not group.strip():
                continue
            
            parts = group.strip().split(',')
            if len(parts) >= 1:
                try:
                    key = int(parts[0].strip())
                    if key in ATTRIBUTE_MAP:
                        attributes_set.add(ATTRIBUTE_MAP[key])
                except (ValueError, KeyError):
                    continue
        
        return ','.join(sorted(attributes_set))
    
    df_level_conf['attribute'] = df_level_conf['target'].apply(parse_target_attributes)
    
    # 调整列顺序
    if 'target_num' in df_level_conf.columns:
        target_num_idx = df_level_conf.columns.get_loc('target_num')
        cols = list(df_level_conf.columns)
        cols.insert(target_num_idx + 1, cols.pop(cols.index('attribute')))
        df_level_conf = df_level_conf[cols]
    
    return df_level_conf


def process_evaluation_conf(df_level_conf: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """
    处理df_level_conf中的evaluation列
    """
    df_level_conf = df_level_conf.copy()
    
    # 创建level_name到evaluation列表的映射
    level_evaluation_dict = {}
    
    for _, row in df.iterrows():
        level_name = row['level_name']
        evaluation = row['evaluation']
        
        if pd.isna(level_name) or pd.isna(evaluation):
            continue
        
        if level_name not in level_evaluation_dict:
            level_evaluation_dict[level_name] = []
        
        level_evaluation_dict[level_name].append(str(evaluation))
    
    def get_evaluations_for_level(level_name):
        if pd.isna(level_name):
            return ""
        
        evaluations = level_evaluation_dict.get(level_name, [])
        return ','.join(evaluations)
    
    df_level_conf['evaluation'] = df_level_conf['level_name'].apply(get_evaluations_for_level)
    return df_level_conf


def process_rec_difficulty(df_level_conf: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """
    处理rec_difficulty列
    """
    df_level_conf = df_level_conf.copy()
    
    # 创建level_name到fuuu值的映射
    level_fuuu_dict = {}
    
    for _, row in df.iterrows():
        level_name = row['level_name']
        evaluation = row['evaluation']
        fuuu_value = row['fuuu']
        
        if pd.isna(level_name) or pd.isna(fuuu_value):
            continue
        
        # 条件：evaluation为空值或>=0
        if pd.isna(evaluation) or evaluation >= 0:
            if level_name not in level_fuuu_dict:
                level_fuuu_dict[level_name] = set()
            
            try:
                fuuu_int = int(fuuu_value)
                level_fuuu_dict[level_name].add(fuuu_int)
            except (ValueError, TypeError):
                continue
    
    def calculate_rec_difficulty(level_name):
        if pd.isna(level_name):
            return ""
        
        fuuu_values = level_fuuu_dict.get(level_name, set())
        if not fuuu_values:
            return ""
        
        mapped_values = set()
        for fuuu_val in fuuu_values:
            if fuuu_val in FUUU_EVA:
                mapped_values.add(FUUU_EVA[fuuu_val])
        
        return ','.join(sorted(str(val) for val in mapped_values))
    
    df_level_conf['rec_difficulty'] = df_level_conf['level_name'].apply(calculate_rec_difficulty)
    return df_level_conf


def adjust_column_order(df_level_conf: pd.DataFrame) -> pd.DataFrame:
    """
    调整列顺序：将evaluation和rec_difficulty放到attribute后面
    """
    df_level_conf = df_level_conf.copy()
    cols = list(df_level_conf.columns)
    
    if 'attribute' in cols:
        attr_idx = cols.index('attribute')
        
        # 移除evaluation和rec_difficulty列（如果存在）
        if 'evaluation' in cols:
            cols.remove('evaluation')
        if 'rec_difficulty' in cols:
            cols.remove('rec_difficulty')
        
        # 在attribute列后面插入
        cols.insert(attr_idx + 1, 'evaluation')
        cols.insert(attr_idx + 2, 'rec_difficulty')
        
        df_level_conf = df_level_conf[cols]
    
    return df_level_conf


def run_full_pipeline(df_raw: pd.DataFrame, 
                     df_level_conf: pd.DataFrame, 
                     df_level_group: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    运行完整的数据处理流水线
    """
    print("开始数据处理流程...")
    
    # 处理主数据
    df = df_raw.copy()
    df = add_level_name(df, df_level_group)
    df = add_churn_rate(df)
    df = calculate_rev(df)
    df = add_actual_rev(df)
    df = add_zscore(df)
    df = add_fuuu(df)
    df = add_evaluation(df)
    
    # 处理配置数据
    df_level_conf = df_level_conf.copy()
    df_level_conf = process_attribute(df_level_conf)
    df_level_conf = process_evaluation_conf(df_level_conf, df)
    df_level_conf = process_rec_difficulty(df_level_conf, df)
    df_level_conf = adjust_column_order(df_level_conf)
    
    print("数据处理完成！")
    return df, df_level_conf, df_level_group