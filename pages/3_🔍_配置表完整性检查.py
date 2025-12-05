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

def plotly_to_html(fig):
    """将plotly图表转换为HTML字符串"""
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

def create_version_completeness_chart(df_level_group):
    """创建Event Version完整性图表 - 鲜艳彩色版"""
    fig = go.Figure()
    
    # 跳过前2行数据
    df_plot = df_level_group.iloc[2:]  # 从第3行开始
    
    # 获取唯一的版本号并排序
    unique_versions = sorted(df_plot['ap_config_version'].astype(str).unique())
    
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
    for i, version in enumerate(unique_versions):
        color_map[version] = bright_colors[i % len(bright_colors)]
    
    # 遍历每个版本并添加散点
    for version in unique_versions:
        subset = df_plot[df_plot['ap_config_version'].astype(str) == version]
        
        fig.add_trace(go.Scatter(
            x=subset['event_id'].astype(str),
            y=subset['ap_config_version'].astype(str),
            mode='markers',
            marker=dict(
                symbol='diamond',
                size=10,
                color=color_map[version],
                opacity=1
            ),
            name=f'Version {version}',
            hovertemplate='<b>Event ID:</b> %{x}<br><b>Version:</b> %{y}<extra></extra>'
        ))

        fig.update_layout(
            xaxis_title='EventID',
            yaxis_title='Version',
            legend=False,
            height=500
        )
    
    return fig

def find_missing_levels_with_context(df_group, df_conf):
    """
    找出缺失的元素，并关联它们所在行的event_id和ap_config_version
    """
    try:
        # 获取df_conf中的所有level_name
        conf_levels = set(df_conf['level_name'].dropna().astype(str).tolist())
        
        # 用于存储结果的列表
        missing_records = []
        
        # 要检查的列
        columns_to_check = ['level_name_list', 'hidden_level_list']
        
        # 跳过前2行数据
        df_plot = df_group.iloc[2:] if len(df_group) > 2 else df_group
        
        for col in columns_to_check:
            # 遍历df_level_group的每一行
            for idx, row in df_plot.iterrows():
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
            
            # 排序
            unique_df = unique_df.sort_values(['level_name', 'event_id', 'ap_config_version'])
            
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
    with st.spinner("正在处理配置表..."):
        try:
            # 1. 读取所有sheet
            all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            st.session_state.all_sheets = all_sheets
            
            # 获取关键sheet
            df_level_group = all_sheets.get('level_group', pd.DataFrame())
            df_level_conf = all_sheets.get('level_conf', pd.DataFrame())
            
            # 第一部分：查看所有sheet
            st.markdown("### 📋 表结构")
            
            # 使用columns展示sheet信息
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"配置表包含 **{len(all_sheets)}** 个sheet")
                
            with col2:
                st.metric("level_conf行数", len(df_level_conf))
                st.metric("level_group行数", len(df_level_group))
            
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
            st.dataframe(sheet_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # 第二部分：展示图表
            st.markdown("### 📊 Event Version 完整性")
            
            if not df_level_group.empty:
                # 创建图表
                fig = create_version_completeness_chart(df_level_group)
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
            
            if not df_level_group.empty and not df_level_conf.empty:
                # 查找缺失记录
                missing_df = find_missing_levels_with_context(df_level_group, df_level_conf)
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
                if df_level_group.empty:
                    st.warning("⚠️ 未找到level_group sheet")
                if df_level_conf.empty:
                    st.warning("⚠️ 未找到level_conf sheet")
            
        except Exception as e:
            st.error(f"处理文件时出错: {str(e)}")
else:
    st.info("请在左侧上传Events&Level配置表文件")


