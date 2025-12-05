# pages/🎯_模拟分析.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime
import io
import json
import os
import tempfile
import base64
from jinja2 import Environment, FileSystemLoader

# 从config导入配置
from config import FUUU_NEW, MULTIPLIER, FUUU_LIMITS_DATA

# 页面配置
st.set_page_config(
    page_title="模拟分析",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 模拟分析")
st.markdown("---")

# 文件上传区域
st.sidebar.header("📁 数据上传")
uploaded_stats = st.sidebar.file_uploader(
    "上传模拟统计数据 (simulatorStatistics.json)",
    type=['json']
)
uploaded_config = st.sidebar.file_uploader(
    "上传关卡配置表 (Events&Level_upload_*.xlsx)",
    type=['xlsx']
)

# 初始化session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_level' not in st.session_state:
    st.session_state.df_level = None
if 'summary_table' not in st.session_state:
    st.session_state.summary_table = None
if 'abnormal_table' not in st.session_state:
    st.session_state.abnormal_table = None
if 'html_report' not in st.session_state:
    st.session_state.html_report = None
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'chart_data1' not in st.session_state:
    st.session_state.chart_data1 = None
if 'chart_data2' not in st.session_state:
    st.session_state.chart_data2 = None
if 'table1' not in st.session_state:
    st.session_state.table1 = None
if 'table2' not in st.session_state:
    st.session_state.table2 = None
if 'table3' not in st.session_state:
    st.session_state.table3 = None

def load_and_process_data(stats_file, config_file):
    """加载和处理数据"""
    try:
        # 1. 加载模拟统计数据
        df = pd.read_json(stats_file)
        
        # 添加level_id
        df['level_id'] = pd.factorize(df['level_name'])[0] + 1
        
        # 2. 添加fuuu数据
        df_fuuu = pd.DataFrame({'fuuu': FUUU_NEW})
        df_fuuu['level_id'] = range(1, len(df_fuuu) + 1)
        df_fuuu = df_fuuu[['level_id', 'fuuu']]
        df = pd.merge(df, df_fuuu, on=['level_id'], how='left')
        
        # 3. 加载配置表
        df_target = pd.read_excel(config_file, sheet_name='level_conf')
        df_target = df_target[['level_name', 'target']]
        df_target = df_target.drop([0, 1]).reset_index(drop=True)
        
        # 处理target列
        def split_targets(row):
            row = str(row)
            pairs = row.split(';')
            data = {}
            for i, pair in enumerate(pairs):
                if ',' in pair:
                    target, num = pair.split(',')
                    data[f'target{i+1}'] = target
                    data[f'targetnum{i+1}'] = int(num)
            return pd.Series(data)
        
        df_target_split = df_target['target'].apply(split_targets)
        df_target = pd.concat([df_target, df_target_split], axis=1)
        
        # 计算总目标数
        def calculate_total_target(row):
            total = 0
            i = 1
            while f'target{i}' in row and f'targetnum{i}' in row:
                target = row[f'target{i}']
                num = row[f'targetnum{i}']
                if pd.isna(target) or pd.isna(num):
                    i += 1
                    continue
                try:
                    target = int(target)
                    num = int(num)
                    multiplier_value = MULTIPLIER.get(target, 0)
                    total += multiplier_value * num
                except:
                    pass
                i += 1
            return total
        
        df_target['totaltarget'] = df_target.apply(calculate_total_target, axis=1)
        df_target_final = df_target[['level_name', 'totaltarget']]
        
        # 合并到主df
        df = pd.merge(df, df_target_final, on=['level_name'], how='left')
        
        # 4. 计算fuuu_result和fuuu_error
        def calculate_fuuu_result(row):
            if not row['is_win']:
                return row['final_lost_number']
            else:
                h = row['last_10steps_avg_height']
                if 8 < h <= 10:
                    return 0
                elif 7.5 < h <= 8:
                    return -1
                elif 7 < h <= 7.5:
                    return -2
                elif 6.5 < h <= 7:
                    return -3
                elif 6 < h <= 6.5:
                    return -4
                elif 5.5 < h <= 6:
                    return -5
                elif 5 < h <= 5.5:
                    return -6
                else:
                    return -7
        
        df['fuuu_result'] = df.apply(calculate_fuuu_result, axis=1)
        df['fuuu_error'] = (df['fuuu_result'] - df['fuuu']).clip(lower=-10, upper=10)
        
        return df, df_target_final
        
    except Exception as e:
        st.error(f"数据处理错误: {str(e)}")
        return None, None

def generate_summary(df):
    """生成汇总统计"""
    loop_count = df[df['level_id'] == 1].shape[0]
    avg_user_ability = df['user_ability'].mean()
    total_count = len(df)
    win_count = df['is_win'].sum()
    lose_count = total_count - win_count
    totaltarget = df['totaltarget'].mean()
    
    # 避免除以0
    relative_win_rate = df[(df['is_win'] == True) & (df['fuuu_result'] == 0)].shape[0] / win_count if win_count > 0 else np.nan
    relative_lose_rate = df[(df['is_win'] == False) & (df['fuuu_result'] == 1)].shape[0] / lose_count if lose_count > 0 else np.nan
    avg_slide_number = df['slide_number'].mean()
    
    # 格式化函数
    def format_percent(x):
        return f"{x * 100:.2f}%" if pd.notnull(x) else "NaN"
    
    def format_number(x):
        return f"{x:.2f}" if pd.notnull(x) else "NaN"
    
    # 构建 summary DataFrame
    summary_data = {
        '指标': [
            '循环次数',
            '能力',
            '首赢率',
            '险胜率（相对）',
            '惜败率（相对）',
            '平均步数',
            '平均目标物数量'
        ],
        '数值': [
            loop_count,
            format_number(avg_user_ability),
            format_percent(win_count / total_count),
            format_percent(relative_win_rate),
            format_percent(relative_lose_rate),
            format_number(avg_slide_number),
            format_number(totaltarget)
        ]
    }
    return pd.DataFrame(summary_data)

def generate_level_metrics(df):
    """生成关卡级别指标"""
    grouped = df.groupby(['level_id', 'level_name'])
    win_df = df[df['is_win'] == True].copy()
    
    # 计算各项指标
    avg_slide = grouped['slide_number'].mean().rename('平均步数')
    avg_win_slide = win_df.groupby(['level_id', 'level_name'])['slide_number'].mean().rename('平均获胜步数')
    win_rate = grouped['is_win'].mean().rename('首赢率')
    fuuu_avg = grouped['fuuu'].mean().rename('fuuu')
    var_steps = grouped['slide_number'].var().rename('步数方差')
    
    # 合并指标
    df_level_new = pd.concat([
        fuuu_avg,
        win_rate,
        avg_slide,
        avg_win_slide,
        var_steps
    ], axis=1).reset_index().round(2)
    
    return df_level_new

def check_abnormal_levels(df_level, df_limits):
    """检查异常关卡"""
    def get_fuuu_range(value):
        if value >= 5:
            return "[5, ∞]"
        elif value >= 2:
            return "[2, 4]"
        elif value >= -1:
            return "[-1, 1]"
        elif value >= -4:
            return "[-4, -2]"
        else:
            return "[-∞, -5]"
    
    abnormal_rows = []
    
    for _, row in df_level.iterrows():
        fuuu_val = row['fuuu']
        fuuu_range = get_fuuu_range(fuuu_val)
        limit_row = df_limits[df_limits['fuuu区间'] == fuuu_range].iloc[0]
        
        violations = []
        
        def check(metric_cn, col_name):
            val = row[col_name]
            upper = limit_row[f"{metric_cn}上限"]
            lower = limit_row[f"{metric_cn}下限"]
            if pd.notnull(val):
                if val > upper:
                    violations.append(f"{metric_cn}超上限({val:.2f} > {upper})")
                elif val < lower:
                    violations.append(f"{metric_cn}低于下限({val:.2f} < {lower})")
        
        check("首胜率", "首赢率")
        check("步数方差", "步数方差")
        
        if violations:
            abnormal_rows.append({
                "level_id": row["level_id"],
                "level_name": row["level_name"],
                "fuuu": round(fuuu_val, 2),
                "平均步数": row["平均步数"],
                "首赢率": row["首赢率"],
                "步数方差": row["步数方差"],
                "异常项": "; ".join(violations)
            })
    
    return pd.DataFrame(abnormal_rows)

def create_plotly_chart1(df_level_filtered_80):
    """创建第一个图表：关卡指标趋势"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 添加平均获胜步数的线
    fig.add_trace(
        go.Scatter(x=df_level_filtered_80['level_id'], y=df_level_filtered_80['平均获胜步数'], 
                   mode='lines+markers', name='平均获胜步数', line=dict(color='red')),
        secondary_y=False
    )
    
    # 添加fuuu的线
    fig.add_trace(
        go.Scatter(x=df_level_filtered_80['level_id'], y=df_level_filtered_80['fuuu'], 
                   mode='lines+markers', name='fuuu', line=dict(color='blue')),
        secondary_y=True
    )
    
    # 设置坐标轴标题
    fig.update_layout(
        title='Goal Number and Average Steps by LevelID',
        xaxis_title='LevelID',
        height=600,
        margin=dict(l=80, r=0, t=40, b=80),
        legend_title='Metrics',
        legend=dict(
            x=0.7,       
            y=1.2,   
            xanchor='right',  
            yanchor='top',    
            orientation='v' 
        )
    )
    
    # 设置 Y 轴标题
    fig.update_yaxes(title_text='平均获胜步数', secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text='fuuu', secondary_y=True, showgrid=False)
    
    # 生成图表div
    return pyo.plot(fig, include_plotlyjs=False, output_type='div')

def create_plotly_chart2(df):
    """创建第二个图表：FUUU Error分布"""
    bins = np.arange(-10, 11 + 1) - 0.5
    fuuu_error_hist = np.histogram(df['fuuu_error'], bins=bins)
    fuuu_error_percentage = fuuu_error_hist[0] / np.sum(fuuu_error_hist[0]) * 1.0000
    
    fig = go.Figure()
    
    # 添加主直方图
    fig.add_trace(go.Bar(
        x=fuuu_error_hist[1][:-1],
        y=fuuu_error_percentage,
        name='模拟器',
        marker_color='blue',
        opacity=1,
        hoverinfo='y'
    ))
    
    # 更新布局
    fig.update_layout(
        title='FUUU Error Histograms (Percentage)',
        xaxis_title='FUUU Error',
        yaxis_title='Percentage (%)',
        barmode='overlay',
        xaxis=dict(tickvals=np.arange(-10, 11, 1)),
        legend=dict(title='', traceorder='normal', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=600
    )
    
    fig.update_yaxes(tickformat=".1%")
    
    # 生成图表div
    return pyo.plot(fig, include_plotlyjs=False, output_type='div')

def format_level_evaluation(val):
    """格式化关卡评估列"""
    if pd.isna(val) or str(val).strip() == '':
        return val
    
    # 如果值是字符串，处理颜色标记
    val_str = str(val)
    numbers = val_str.split(',')
    formatted_numbers = []
    for num in numbers:
        num = num.strip()
        if num.startswith('-'):
            formatted_numbers.append(f'<span style="color:red;">{num}</span>')
        else:
            formatted_numbers.append(num)
    return ','.join(formatted_numbers)

def generate_html_report():
    """生成HTML报告"""
    try:
        # 读取template.html
        with open('template.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 替换占位符
        html_content = template_content
        replacements = {
            '{{ table1 }}': st.session_state.table1_html,
            '{{ chart_data1 }}': st.session_state.chart_html1,
            '{{ chart_data2 }}': st.session_state.chart_html2,
            '{{ table2 }}': st.session_state.table2_html,
            '{{ table3 }}': st.session_state.table3_html,
            '{{ title }}': 'Jewel Simulation Report',
            '{{ subtitle1 }}': 'Summary',
            '{{ subtitle2 }}': 'Level',
            '{{ subtitle3 }}': 'Event'
        }
        
        for placeholder, value in replacements.items():
            if value:
                html_content = html_content.replace(placeholder, value)
        
        return html_content
        
    except Exception as e:
        st.error(f"生成HTML报告时出错: {str(e)}")
        return None

def plotly_to_html(fig):
    """将plotly图表转换为HTML字符串"""
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

# 主处理流程
if uploaded_stats and uploaded_config:
    with st.spinner("正在处理数据..."):
        # 处理数据
        df, df_target_final = load_and_process_data(uploaded_stats, uploaded_config)
        
        if df is not None:
            # 保存到session state
            st.session_state.df = df
            
            # 1. 生成汇总统计
            summary_df = generate_summary(df)
            st.session_state.summary_table = summary_df
            st.session_state.table1_html = summary_df.to_html(classes='table table-striped', index=False)
            
            # 2. 生成关卡级别指标
            df_level = generate_level_metrics(df)
            
            # 3. 检查异常关卡
            df_limits_df = pd.DataFrame(FUUU_LIMITS_DATA)
            abnormal_df = check_abnormal_levels(df_level, df_limits_df)
            st.session_state.abnormal_table = abnormal_df
            
            # 4. 合并目标物数量
            df_level = pd.merge(df_level, df_target_final, on='level_name', how='left')
            df_level_filtered = df_level[df_level['level_id'] <= 80]
            
            st.session_state.df_level = df_level_filtered
            
            # 5. 生成HTML表格和图表
            # 生成table2（关卡数据）
            df_level_display = df_level_filtered.copy()
            df_level_display = df_level_display[['level_id', 'level_name', 'fuuu', '首赢率', '平均步数', '平均获胜步数', '步数方差']]
            df_level_display.rename(columns={
                'level_id': '关卡ID',
                'level_name': '关卡名称',
                'fuuu': 'fuuu',
                '首赢率': '首赢率',
                '平均步数': '平均步数',
                '平均获胜步数': '平均获胜步数',
                '步数方差': '步数方差'
            }, inplace=True)
            st.session_state.table2_html = df_level_display.to_html(classes='table table-striped', index=False, escape=False)
            
            # 生成table3（异常关卡）
            if len(abnormal_df) > 0:
                st.session_state.table3_html = abnormal_df.to_html(classes='table table-striped', index=False)
            else:
                st.session_state.table3_html = "<p>没有发现异常关卡</p>"
            
            # 生成图表数据
            chart1 = create_chart1(df_level_filtered)
            chart2 = create_chart2(df)
            
            st.session_state.chart_html1 = plotly_to_html(chart1)
            st.session_state.chart_html2 = plotly_to_html(chart2)
            
            st.success("数据处理完成！")
            st.session_state.report_generated = True
else:
    st.info("请先在左侧上传模拟统计数据(simulatorStatistics.json)和关卡配置表(xlsx)")

# 显示结果和报告
if st.session_state.report_generated:
    # 先在Streamlit中显示关键结果
    st.markdown("### 📊 关键指标")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("总关卡数", st.session_state.df_level.shape[0])
    
    with col2:
        win_rate = st.session_state.df['is_win'].mean()
        st.metric("总体首赢率", f"{win_rate:.1%}")
    
    with col3:
        if st.session_state.abnormal_table is not None:
            st.metric("异常关卡数", len(st.session_state.abnormal_table))
    
    # 显示图表
    st.markdown("### 📈 分析图表")
    
    tab1, tab2 = st.tabs(["关卡指标趋势", "FUUU Error分布"])
    
    with tab1:
        if st.session_state.chart_html1:
            st.components.v1.html(st.session_state.chart_html1, height=550)
    
    with tab2:
        if st.session_state.chart_html2:
            st.components.v1.html(st.session_state.chart_html2, height=550)
    
    # 显示数据表格
    st.markdown("### 📋 详细数据")
    
    data_tabs = st.tabs(["汇总统计", "关卡指标", "异常检测"])
    
    with data_tabs[0]:
        st.dataframe(st.session_state.summary_table, use_container_width=True)
    
    with data_tabs[1]:
        st.dataframe(st.session_state.df_level, use_container_width=True)
    
    with data_tabs[2]:
        if st.session_state.abnormal_table is not None and len(st.session_state.abnormal_table) > 0:
            st.dataframe(st.session_state.abnormal_table, use_container_width=True)
        else:
            st.success("✅ 未检测到异常关卡")
    
    st.markdown("---")
    
    # HTML报告部分
    st.markdown("### 📄 HTML报告生成")
    
    # 生成并显示HTML报告
    if st.button("生成完整HTML报告", type="primary"):
        with st.spinner("正在生成HTML报告..."):
            html_content = generate_html_report()
            if html_content:
                st.session_state.html_report = html_content
                
                # 在Streamlit中显示报告
                st.markdown("#### 报告预览")
                
                # 方法1：使用iframe显示完整报告
                html_with_wrapper = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            margin: 0;
                            padding: 20px;
                            background-color: #f0f2f6;
                        }}
                        .report-container {{
                            max-width: 1200px;
                            margin: 0 auto;
                            background: white;
                            padding: 30px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }}
                    </style>
                </head>
                <body>
                    <div class="report-container">
                        {html_content}
                    </div>
                </body>
                </html>
                """
                
                # 显示HTML报告
                st.components.v1.html(html_with_wrapper, height=1000, scrolling=True)
                
                # 下载按钮
                st.markdown("---")
                st.markdown("#### 💾 下载报告")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 下载HTML报告
                    b64 = base64.b64encode(html_content.encode()).decode()
                    filename = f"level_simulation_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration: none;">' \
                           f'<button style="background-color: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">' \
                           f'📥 下载HTML报告</button></a>'
                    st.markdown(href, unsafe_allow_html=True)
                
                with col2:
                    # 下载异常关卡数据
                    if st.session_state.abnormal_table is not None and len(st.session_state.abnormal_table) > 0:
                        csv = st.session_state.abnormal_table.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 下载异常关卡数据(CSV)",
                            data=csv,
                            file_name=f"abnormal_levels_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                
                # 提供查看HTML源码的选项
                with st.expander("查看HTML源码"):
                    st.code(html_content[:5000] + "..." if len(html_content) > 5000 else html_content, language='html')
