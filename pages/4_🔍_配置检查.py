# pages/3_🔍_配置表完整性检查.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO
import warnings
warnings.filterwarnings("ignore")

# 页面配置
st.set_page_config(
    page_title="配置表完整性检查",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 配置表完整性检查")
st.markdown("---")

# 文件上传区域
st.sidebar.header("📁 上传配置表")
uploaded_file = st.sidebar.file_uploader(
    "上传Events&Level配置表 (xls/xlsx)",
    type=['xls', 'xlsx']
)

# 初始化session state
if 'all_sheets' not in st.session_state:
    st.session_state.all_sheets = None
if 'chart_html' not in st.session_state:
    st.session_state.chart_html = None
if 'missing_df' not in st.session_state:
    st.session_state.missing_df = None
if 'level_generation_df' not in st.session_state:
    st.session_state.level_generation_df = None

def plotly_to_html(fig):
    """将plotly图表转换为HTML字符串"""
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

def clean_dataframe_columns(df):
    """清理DataFrame列名"""
    if df is not None and not df.empty:
        # 去除列名中的空白字符
        df.columns = df.columns.str.strip()
    return df

def skip_first_two_data_rows(df):
    """跳过DataFrame的第2行和第3行数据（保留表头，忽略第2-3行）"""
    if df is not None and len(df) >= 3:  # 至少有表头+2行数据
        # 保留表头，跳过第1行之后的两行数据（即第2行和第3行）
        return df.iloc[3:].reset_index(drop=True)
    elif df is not None and len(df) == 2:  # 只有表头+1行数据
        return df.iloc[2:].reset_index(drop=True)
    return df

def get_clean_data(df):
    """获取清理后的数据，跳过第2-3行"""
    df = clean_dataframe_columns(df)
    df = skip_first_two_data_rows(df)
    return df

def safe_sort_unique(values):
    """安全地排序唯一值，处理混合类型"""
    if len(values) == 0:
        return []
    
    # 转换为字符串并去重
    str_values = []
    for v in values:
        if pd.notna(v):
            str_val = str(v).strip()
            if str_val:  # 只添加非空字符串
                str_values.append(str_val)
    
    # 去重
    unique_values = list(set(str_values))
    
    # 尝试将可以转换为数字的值转换
    numeric_values = []
    non_numeric_values = []
    
    for val in unique_values:
        try:
            # 尝试转换为数字
            if '.' in val or 'e' in val.lower():
                # 尝试转换为浮点数
                num_val = float(val)
            else:
                # 尝试转换为整数
                num_val = int(val)
            numeric_values.append(num_val)
        except (ValueError, TypeError):
            non_numeric_values.append(val)
    
    # 分别排序数字和非数字
    numeric_values.sort()
    non_numeric_values.sort()
    
    # 合并结果（数字在前，字符串在后）
    result = numeric_values + non_numeric_values
    return result

def generate_first_60_levels(event_id, ap_config_version, df_level_group, df_level_conf):
    """
    生成前60关配置表
    """
    try:
        # 清理数据并跳过第2-3行
        df_level_group_clean = get_clean_data(df_level_group)
        df_level_conf_clean = get_clean_data(df_level_conf)
        
        # 显示调试信息
        with st.expander("数据调试信息", expanded=False):
            st.write(f"查找参数: event_id={event_id}, version={ap_config_version}")
            st.write(f"level_group原始数据行数: {len(df_level_group)}")
            st.write(f"level_group清理后数据行数 (已忽略第2-3行): {len(df_level_group_clean)}")
            st.write(f"level_conf原始数据行数: {len(df_level_conf)}")
            st.write(f"level_conf清理后数据行数 (已忽略第2-3行): {len(df_level_conf_clean)}")
            if not df_level_group_clean.empty:
                st.write("level_group清理后的前5行数据:")
                st.dataframe(df_level_group_clean.head())
            if not df_level_conf_clean.empty:
                st.write("level_conf清理后的前5行数据:")
                st.dataframe(df_level_conf_clean.head())
        
        if df_level_group_clean.empty or df_level_conf_clean.empty:
            st.error("数据为空，请检查Excel文件格式")
            return None
        
        # 在level_group中查找匹配的行 - 使用字符串比较
        found_row = None
        search_event_id = str(event_id).strip()
        search_version = str(ap_config_version).strip()
        
        for _, row in df_level_group_clean.iterrows():
            row_event_id = str(row.get('event_id', '')).strip()
            row_version = str(row.get('ap_config_version', '')).strip()
            
            if row_event_id == search_event_id and row_version == search_version:
                found_row = row
                break
        
        if found_row is None:
            # 显示可用的选项
            unique_events = df_level_group_clean['event_id'].dropna().unique()
            unique_versions = df_level_group_clean['ap_config_version'].dropna().unique()
            
            sorted_events = safe_sort_unique(unique_events)
            sorted_versions = safe_sort_unique(unique_versions)
            
            st.error(f"未找到 event_id={search_event_id}, ap_config_version={search_version} 的记录")
            st.info(f"可用的 Event IDs (前20个): {', '.join(map(str, sorted_events[:20]))}{'...' if len(sorted_events) > 20 else ''}")
            st.info(f"可用的 Versions (前20个): {', '.join(map(str, sorted_versions[:20]))}{'...' if len(sorted_versions) > 20 else ''}")
            return None
        
        # 获取level_name_list
        level_name_list_str = str(found_row.get('level_name_list', ''))
        
        if pd.isna(level_name_list_str) or level_name_list_str.strip() == '':
            st.error("level_name_list为空")
            return None
        
        # 拆分level_name_list
        level_names = [name.strip() for name in level_name_list_str.split(',') if name.strip()]
        
        # 只取前60个
        level_names = level_names[:60]
        
        if not level_names:
            st.error("level_name_list中没有有效的关卡名")
            return None
        
        # 创建基础DataFrame
        result_data = []
        
        # 准备level_conf的查找字典（提高查找效率）
        level_conf_dict = {}
        if 'level_name' in df_level_conf_clean.columns:
            for _, row in df_level_conf_clean.iterrows():
                level_name = str(row.get('level_name', '')).strip()
                if level_name:
                    level_conf_dict[level_name] = row
        
        st.write(f"找到 {len(level_names)} 个关卡，正在从level_conf中查找对应信息...")
        
        for idx, level_name in enumerate(level_names, 1):
            # 在level_conf字典中查找对应的level
            level_conf_data = level_conf_dict.get(level_name)
            
            if level_conf_data is None:
                # 如果找不到对应的level_conf记录，使用空值
                difficulty = None
                target_type = None
                category = None
                map_above = None
                map_below = None
            else:
                # 处理difficulty：如果为0则显示为空
                difficulty = level_conf_data.get('difficulty')
                if pd.isna(difficulty):
                    difficulty = None
                elif isinstance(difficulty, (int, float)):
                    if difficulty == 0:
                        difficulty = None
                elif isinstance(difficulty, str):
                    try:
                        diff_val = float(difficulty)
                        if diff_val == 0:
                            difficulty = None
                        else:
                            difficulty = diff_val
                    except:
                        difficulty = None
                
                # 获取其他字段
                target_type = level_conf_data.get('target_type')
                category = level_conf_data.get('category')
                map_above = level_conf_data.get('map_above')
                map_below = level_conf_data.get('map_below')
            
            result_data.append({
                'level_id': idx,
                'difficulty': difficulty,
                'target_type': target_type,
                'category': category,
                'map_above': map_above,
                'map_below': map_below
            })
        
        # 创建DataFrame
        result_df = pd.DataFrame(result_data)
        
        return result_df
        
    except Exception as e:
        st.error(f"生成配置表时出错: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def create_version_completeness_chart(df_level_group):
    """创建Event Version完整性图表 - 鲜艳彩色版"""
    try:
        fig = go.Figure()
        
        if df_level_group.empty:
            return fig
        
        # 清理数据并跳过第2-3行
        df_plot = get_clean_data(df_level_group)
        
        if df_plot.empty:
            return fig
        
        # 获取唯一的版本号
        unique_versions = df_plot['ap_config_version'].dropna().unique()
        
        # 安全排序
        sorted_versions = safe_sort_unique(unique_versions)
        
        if not sorted_versions:
            return fig
        
        # 鲜艳的颜色方案
        bright_colors = [
            '#FF6B6B',  # 珊瑚红
            '#4ECDC4',  # 青绿色
            '#FFD166',  # 金黄色
            '#06D6A0',  # 薄荷绿
            '#118AB2',  # 宝蓝色
            '#EF476F',  # 粉红色
            '#073B4C',  # 深蓝色
            '#7209B7',  # 紫色
            '#F72585',  # 洋红色
            '#3A86FF',  # 亮蓝色
            '#FB5607',  # 橙色
            '#8338EC',  # 紫罗兰色
        ]
        
        # 为每个版本分配颜色
        color_map = {}
        for i, version in enumerate(sorted_versions):
            version_str = str(version)
            color_map[version_str] = bright_colors[i % len(bright_colors)]
        
        # 遍历每个版本并添加散点
        for version in sorted_versions:
            version_str = str(version)
            # 使用字符串匹配
            mask = df_plot['ap_config_version'].astype(str).str.strip() == version_str
            subset = df_plot[mask]
            
            if len(subset) > 0:
                fig.add_trace(go.Scatter(
                    x=subset['event_id'].astype(str).str.strip(),
                    y=[version_str] * len(subset),
                    mode='markers',
                    marker=dict(
                        symbol='diamond',
                        size=10,
                        color=color_map[version_str],
                        opacity=1
                    ),
                    name='',  # 设置为空字符串
                    showlegend=False,  # 明确设置为不显示图例
                    hovertemplate='<b>Event ID:</b> %{x}<br><b>Version:</b> %{y}<extra></extra>'
                ))

        fig.update_layout(
            title='Event AP Config Version',
            xaxis_title='EventID',
            yaxis_title='Version',
            showlegend=False, 
            yaxis=dict(
                tickvals=[str(v) for v in sorted_versions],
                tickmode='array'
            ),
            height=500
        )
        
        return fig
    except Exception as e:
        st.error(f"创建图表时出错: {str(e)}")
        return go.Figure()

def find_missing_levels_with_context(df_group, df_conf):
    """
    找出缺失的元素，并关联它们所在行的event_id和ap_config_version
    """
    try:
        # 清理数据并跳过第2-3行
        df_group_clean = get_clean_data(df_group)
        df_conf_clean = get_clean_data(df_conf)
        
        if df_group_clean.empty or df_conf_clean.empty:
            return pd.DataFrame(columns=['level_name', 'event_id', 'ap_config_version'])
        
        # 获取df_conf中的所有level_name
        conf_levels = set(df_conf_clean['level_name'].dropna().astype(str).str.strip().tolist())
        
        # 用于存储结果的列表
        missing_records = []
        
        # 要检查的列
        columns_to_check = ['level_name_list', 'hidden_level_list']
        
        for col in columns_to_check:
            if col not in df_group_clean.columns:
                continue
                
            # 遍历df_level_group的每一行
            for idx, row in df_group_clean.iterrows():
                if pd.isna(row[col]) or str(row[col]).strip() == '':
                    continue
                
                # 获取该行的event_id和ap_config_version
                event_id = row['event_id']
                ap_version = row['ap_config_version']
                
                # 拆分level列表
                level_list = str(row[col]).split(',')
                level_list = [level.strip() for level in level_list if level.strip()]
                
                # 检查每个level
                for level in level_list:
                    if level not in conf_levels:
                        missing_records.append({
                            'level_name': level,
                            'source_column': col,
                            'event_id': event_id,
                            'ap_config_version': ap_version,
                            'row_index': idx
                        })
        
        # 转换为DataFrame
        if missing_records:
            result_df = pd.DataFrame(missing_records)
            
            # 按缺失元素、event_id、ap_config_version去重
            unique_df = result_df[['level_name', 'event_id', 'ap_config_version']].drop_duplicates()
            
            # 安全排序
            try:
                # 创建字符串副本用于排序
                unique_df = unique_df.copy()
                unique_df['_event_id_str'] = unique_df['event_id'].astype(str).str.strip()
                unique_df['_ap_version_str'] = unique_df['ap_config_version'].astype(str).str.strip()
                unique_df = unique_df.sort_values(['level_name', '_event_id_str', '_ap_version_str'])
                unique_df = unique_df.drop(['_event_id_str', '_ap_version_str'], axis=1)
            except:
                # 如果排序失败，保持原顺序
                pass
            
            # 重置索引
            unique_df = unique_df.reset_index(drop=True)
            
            return unique_df
        else:
            return pd.DataFrame(columns=['level_name', 'event_id', 'ap_config_version'])
            
    except Exception as e:
        st.error(f"查找缺失记录时出错: {str(e)}")
        return pd.DataFrame(columns=['level_name', 'event_id', 'ap_config_version'])

# 主处理流程
if uploaded_file:
    try:
        # 读取所有sheet
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        st.session_state.all_sheets = all_sheets
        
        # 获取关键sheet
        df_level_group_raw = all_sheets.get('level_group', pd.DataFrame())
        df_level_conf_raw = all_sheets.get('level_conf', pd.DataFrame())
        
        # 新增：前60关配置表生成功能 - 放在主流程前面
        if not df_level_group_raw.empty and not df_level_conf_raw.empty:
            st.markdown("### 🎮 前60关配置表生成")
            
            # 获取清理后的数据用于下拉菜单 - 这里已经忽略了第2-3行
            df_level_group_clean = get_clean_data(df_level_group_raw)
            
            if not df_level_group_clean.empty:
                # 显示数据信息
                with st.expander("数据源信息", expanded=False):
                    st.write(f"原始level_group数据行数 (包含表头): {len(df_level_group_raw)}")
                    st.write(f"清理后level_group数据行数 (已忽略第2-3行): {len(df_level_group_clean)}")
                    st.write("清理后的前5行数据:")
                    st.dataframe(df_level_group_clean.head())
                
                # 获取唯一的event_id和version（从清理后的数据）
                unique_event_ids = df_level_group_clean['event_id'].dropna().unique()
                unique_versions = df_level_group_clean['ap_config_version'].dropna().unique()
                
                # 安全排序
                sorted_event_ids = safe_sort_unique(unique_event_ids)
                sorted_versions = safe_sort_unique(unique_versions)
                
                if not sorted_event_ids or not sorted_versions:
                    st.error("清理后的数据中没有有效的Event ID或Version")
                else:
                    # 转换为字符串用于显示
                    event_id_options = [str(x) for x in sorted_event_ids]
                    version_options = [str(x) for x in sorted_versions]
                    
                    # 创建选择器界面
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        selected_event_id_str = st.selectbox(
                            "选择 Event ID",
                            options=event_id_options,
                            key="event_id_selector_main"
                        )
                    
                    with col2:
                        selected_version_str = st.selectbox(
                            "选择 AP Config Version",
                            options=version_options,
                            key="version_selector_main"
                        )
                    
                    with col3:
                        st.write("")  # 空白行用于垂直对齐
                        st.write("")  # 空白行用于垂直对齐
                        generate_btn = st.button(
                            "🎯 生成前60关配置表",
                            type="primary",
                            use_container_width=True
                        )
                    
                    # 当按钮被点击时生成配置表
                    if generate_btn and selected_event_id_str and selected_version_str:
                        with st.spinner("正在生成配置表..."):
                            result_df = generate_first_60_levels(
                                selected_event_id_str, 
                                selected_version_str, 
                                df_level_group_raw,  # 传入原始数据，函数内部会清理
                                df_level_conf_raw    # 传入原始数据，函数内部会清理
                            )
                            
                            if result_df is not None:
                                st.session_state.level_generation_df = result_df
                                
                                # 显示结果
                                st.success(f"✅ 成功生成前60关配置表 (Event ID: {selected_event_id_str}, Version: {selected_version_str})")
                                
                                # 显示表格
                                st.dataframe(result_df, use_container_width=True, hide_index=True)
                                
                                # 提供下载按钮
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    result_df.to_excel(writer, sheet_name='前60关配置', index=False)
                                output.seek(0)
                                
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    st.download_button(
                                        label="📥 下载前60关配置表 (xlsx)",
                                        data=output,
                                        file_name=f"event_{selected_event_id_str}_v{selected_version_str}_前60关配置.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
            
            st.markdown("---")
        else:
            if df_level_group_raw.empty:
                st.warning("⚠️ 未找到level_group sheet")
            if df_level_conf_raw.empty:
                st.warning("⚠️ 未找到level_conf sheet")
        
        # 第一部分：查看所有sheet
        st.markdown("### 📋 表结构")
        
        # 使用columns展示sheet信息
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info(f"配置表包含 **{len(all_sheets)}** 个sheet")
            
        with col2:
            st.metric("level_conf行数", len(df_level_conf_raw))
            st.metric("level_group行数", len(df_level_group_raw))
        
        # 显示sheet列表
        sheet_data = []
        for i, (sheet_name, df) in enumerate(all_sheets.items(), 1):
            sheet_data.append({
                '序号': i,
                'Sheet名称': sheet_name,
                '行数': df.shape[0],
                '列数': df.shape[1]
            })
        
        sheet_df = pd.DataFrame(sheet_data)
        # 确保数据类型正确
        sheet_df = sheet_df.astype({
            '序号': 'int',
            'Sheet名称': 'str',
            '行数': 'int',
            '列数': 'int'
        })
        st.dataframe(sheet_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 第二部分：展示图表
        st.markdown("### 📊 Event Version 完整性")
        
        if not df_level_group_raw.empty:
            # 创建图表
            fig = create_version_completeness_chart(df_level_group_raw)
            chart_html = plotly_to_html(fig)
            st.session_state.chart_html = chart_html
            
            # 显示图表
            st.components.v1.html(chart_html, height=550)
            
            # 图表说明
            with st.expander("📝 图表说明"):
                st.markdown("""
                **图表解读：**
                - 每个菱形代表一个Event配置
                - X轴：Event ID
                - Y轴：AP Config Version
                - 图表展示了不同版本的事件配置分布情况
                """)
        else:
            st.warning("未找到level_group sheet或sheet为空")
        
        st.markdown("---")
        
        # 第三部分：查找缺失记录
        st.markdown("### 🔎 缺失level_name检查")
        
        if not df_level_group_raw.empty and not df_level_conf_raw.empty:
            # 查找缺失记录
            missing_df = find_missing_levels_with_context(df_level_group_raw, df_level_conf_raw)
            st.session_state.missing_df = missing_df
            
            if len(missing_df) > 0:
                # 显示统计信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("缺失记录数", len(missing_df))
                with col2:
                    st.metric("涉及Level数", missing_df['level_name'].nunique())
                with col3:
                    st.metric("涉及Event数", missing_df['event_id'].nunique())
                
                # 显示缺失记录表格
                st.dataframe(missing_df, use_container_width=True, hide_index=True)
                
            else:
                st.success("✅ 未发现缺失记录，配置表完整！")
        else:
            if df_level_group_raw.empty:
                st.warning("⚠️ 未找到level_group sheet")
            if df_level_conf_raw.empty:
                st.warning("⚠️ 未找到level_conf sheet")
        
    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
else:
    st.info("请在左侧上传Events&Level配置表文件")
