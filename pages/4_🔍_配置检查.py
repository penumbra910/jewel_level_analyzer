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

def generate_first_60_levels(event_id, ap_config_version, df_level_group, df_level_conf):
    """
    生成前60关配置表
    """
    try:
        # 转换event_id和version类型以确保匹配
        if isinstance(event_id, str):
            try:
                event_id = int(float(event_id))
            except:
                pass
        
        if isinstance(ap_config_version, str):
            try:
                ap_config_version = float(ap_config_version)
            except:
                pass
        
        # 在level_group中查找匹配的行
        mask = (df_level_group['event_id'].astype(str) == str(event_id)) & (df_level_group['ap_config_version'].astype(str) == str(ap_config_version))
        matching_rows = df_level_group[mask]
        
        if len(matching_rows) == 0:
            # 尝试更宽松的匹配
            mask = (df_level_group['event_id'].apply(lambda x: str(x).strip()) == str(event_id).strip()) & \
                   (df_level_group['ap_config_version'].apply(lambda x: str(x).strip()) == str(ap_config_version).strip())
            matching_rows = df_level_group[mask]
        
        if len(matching_rows) == 0:
            st.error(f"未找到 event_id={event_id}, ap_config_version={ap_config_version} 的记录")
            return None
        
        if len(matching_rows) > 1:
            st.warning(f"找到多条匹配记录，将使用第一条")
        
        selected_row = matching_rows.iloc[0]
        
        # 获取level_name_list
        level_name_list_str = str(selected_row.get('level_name_list', ''))
        
        if pd.isna(level_name_list_str) or level_name_list_str.strip() == '':
            st.error("level_name_list为空")
            return None
        
        # 拆分level_name_list
        level_names = [name.strip() for name in level_name_list_str.split(',') if name.strip()]
        
        # 只取前60个
        level_names = level_names[:60]
        
        # 创建基础DataFrame
        result_data = []
        
        for idx, level_name in enumerate(level_names, 1):
            # 在level_conf中查找对应的level
            level_conf_row = df_level_conf[df_level_conf['level_name'] == level_name]
            
            if len(level_conf_row) == 0:
                # 如果找不到对应的level_conf记录，使用空值
                difficulty = None
                target_type = None
                category = None
                map_above = None
                map_below = None
            else:
                level_conf_data = level_conf_row.iloc[0]
                
                # 处理difficulty：如果为0则显示为空
                difficulty = level_conf_data.get('difficulty')
                if difficulty == 0 or pd.isna(difficulty):
                    difficulty = None
                
                # 获取其他字段
                target_type = level_conf_data.get('target_type')
                category = level_conf_data.get('category')
                map_above = level_conf_data.get('map_above')
                map_below = level_conf_data.get('map_below')
            
            result_data.append({
                'level_name': level_name,
                'level_id': idx,
                'difficulty': difficulty,
                'target_type': target_type,
                'category': category,
                'map_above': map_above,
                'map_below': map_below
            })
        
        # 创建DataFrame
        result_df = pd.DataFrame(result_data)
        
        # 删除level_name列
        if 'level_name' in result_df.columns:
            result_df = result_df.drop('level_name', axis=1)
        
        return result_df
        
    except Exception as e:
        st.error(f"生成配置表时出错: {str(e)}")
        return None

def create_version_completeness_chart(df_level_group):
    """创建Event Version完整性图表 - 鲜艳彩色版"""
    fig = go.Figure()
    
    # 跳过前2行数据
    df_plot = df_level_group.iloc[2:] if len(df_level_group) > 2 else df_level_group
    
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
            tickvals=unique_versions,
            tickmode='array'
        ),
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
    try:
        # 读取所有sheet
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        st.session_state.all_sheets = all_sheets
        
        # 获取关键sheet
        df_level_group = all_sheets.get('level_group', pd.DataFrame())
        df_level_conf = all_sheets.get('level_conf', pd.DataFrame())
        
        # 新增：前60关配置表生成功能 - 放在主流程前面
        if not df_level_group.empty:
            st.markdown("### 🎮 前60关配置表生成")
            
            # 创建选择器界面
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # 获取唯一的event_id
                unique_event_ids = sorted(df_level_group['event_id'].dropna().unique())
                # 转换为字符串用于显示
                event_id_options = [str(x) for x in unique_event_ids]
                selected_event_id_str = st.selectbox(
                    "选择 Event ID",
                    options=event_id_options,
                    key="event_id_selector_main"
                )
                # 转换回原类型
                selected_event_id = None
                for orig_id in unique_event_ids:
                    if str(orig_id) == selected_event_id_str:
                        selected_event_id = orig_id
                        break
            
            with col2:
                # 获取唯一的ap_config_version
                unique_versions = sorted(df_level_group['ap_config_version'].dropna().unique())
                # 转换为字符串用于显示
                version_options = [str(x) for x in unique_versions]
                selected_version_str = st.selectbox(
                    "选择 AP Config Version",
                    options=version_options,
                    key="version_selector_main"
                )
                # 转换回原类型
                selected_version = None
                for orig_ver in unique_versions:
                    if str(orig_ver) == selected_version_str:
                        selected_version = orig_ver
                        break
            
            with col3:
                st.write("")  # 空白行用于垂直对齐
                generate_btn = st.button(
                    "🎯 生成前60关配置表",
                    type="primary",
                    use_container_width=True
                )
            
            # 当按钮被点击时生成配置表
            if generate_btn and selected_event_id is not None and selected_version is not None:
                with st.spinner("正在生成配置表..."):
                    result_df = generate_first_60_levels(
                        selected_event_id, 
                        selected_version, 
                        df_level_group, 
                        df_level_conf
                    )
                    
                    if result_df is not None:
                        st.session_state.level_generation_df = result_df
                        
                        # 显示结果
                        st.success(f"✅ 成功生成前60关配置表 (Event ID: {selected_event_id}, Version: {selected_version})")
                        
                        # 显示表格
                        st.dataframe(result_df, width='stretch', hide_index=True)
                        
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
                                file_name=f"event_{selected_event_id}_v{selected_version}_前60关配置.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
            
            st.markdown("---")
        
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
        # 确保数据类型正确
        sheet_df = sheet_df.astype({
            '序号': 'int',
            'Sheet名称': 'str',
            '行数': 'int',
            '列数': 'int'
        })
        st.dataframe(sheet_df, width='stretch', hide_index=True)
        
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
                
                # 确保数据类型正确
                missing_df = missing_df.astype({
                    'level_name': 'str',
                    'event_id': 'str',
                    'ap_config_version': 'str'
                })
                # 显示缺失记录表格
                st.dataframe(missing_df, width='stretch', hide_index=True)
                
            else:
                st.success("✅ 未发现缺失记录，配置表完整！")
        else:
            if df_level_group.empty:
                st.warning("⚠️ 未找到level_group sheet")
            if df_level_conf.empty:
                st.warning("⚠️ 未找到level_conf sheet")
        
    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        st.exception(e)
else:
    st.info("请在左侧上传Events&Level配置表文件")
