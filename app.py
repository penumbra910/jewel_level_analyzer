"""
Streamlit主应用
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_processing import run_full_pipeline
from utils.file_utils import (
    read_uploaded_files,
    validate_dataframes,
    generate_excel_output,
    generate_filename
)

# 页面配置
st.set_page_config(
    page_title="游戏关卡数据分析工具",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #bee5eb;
        margin: 10px 0;
    }
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
    }
    .step {
        text-align: center;
        flex: 1;
        padding: 10px;
    }
    .step.active {
        background-color: #1E88E5;
        color: white;
        border-radius: 5px;
    }
    .step.completed {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
def init_session_state():
    """初始化session state"""
    if 'step' not in st.session_state:
        st.session_state.step = 1  # 1:上传, 2:验证, 3:处理, 4:下载
    
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {
            'raw': None,
            'conf': None
        }
    
    if 'dataframes' not in st.session_state:
        st.session_state.dataframes = {
            'df_raw': None,
            'df_level_conf': None,
            'df_level_group': None
        }
    
    if 'validation' not in st.session_state:
        st.session_state.validation = None
    
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    
    if 'result_file' not in st.session_state:
        st.session_state.result_file = None
    
    if 'processing_error' not in st.session_state:
        st.session_state.processing_error = None

# 渲染侧边栏
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🎮 游戏关卡分析")
        st.markdown("---")
        
        st.markdown("### 📋 使用步骤")
        steps = [
            ("1. 上传文件", "上传原始数据和配置文件"),
            ("2. 数据验证", "检查数据格式和完整性"),
            ("3. 数据处理", "执行分析计算"),
            ("4. 下载结果", "获取分析结果文件")
        ]
        
        for i, (step_title, step_desc) in enumerate(steps, 1):
            if i == st.session_state.step:
                st.markdown(f"**▶️ {step_title}**")
                st.caption(step_desc)
            elif i < st.session_state.step:
                st.markdown(f"✅ {step_title}")
                st.caption(step_desc)
            else:
                st.markdown(f"○ {step_title}")
                st.caption(step_desc)
        
        st.markdown("---")
        st.markdown("### ⚙️ 配置参数")
        
        # 可以在这里添加用户可配置的参数
        st.session_state.zscore_threshold = st.slider(
            "Z-score阈值",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.1,
            help="用于确定evaluation的z-score阈值"
        )
        
        st.markdown("---")
        st.markdown("### ℹ️ 关于")
        st.markdown("""
        此工具用于分析游戏关卡数据，
        生成关卡配置和评估结果。
        
        **版本**: 1.0.0
        **最后更新**: 2024-01-15
        """)

# 步骤1: 文件上传
def step_upload():
    """步骤1: 文件上传"""
    st.markdown('<h1 class="main-header">📁 数据上传</h1>', unsafe_allow_html=True)
    
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 原始数据文件")
        st.markdown("""
        上传包含以下列的Excel文件：
        - event_id
        - ap_config_version  
        - lv_id
        - total_churn_rate
        - in_level_churn_rate
        - avg_start_times
        - rv_efficiency
        """)
        
        uploaded_file_raw = st.file_uploader(
            "选择原始数据文件",
            type=['xlsx', 'xls'],
            key="raw_uploader",
            help="上传events_level_raw.xlsx类似的文件"
        )
        
        if uploaded_file_raw:
            st.session_state.uploaded_files['raw'] = uploaded_file_raw
            st.markdown(f'<div class="success-box">✅ 已上传: {uploaded_file_raw.name}</div>', unsafe_allow_html=True)
    
    with col2:
        st.subheader("2. 配置文件")
        st.markdown("""
        上传包含两个sheet的Excel文件：
        
        **Sheet 1: level_conf**
        - level_name
        - target
        
        **Sheet 2: level_group**
        - event_id
        - ap_config_version
        - level_name_list
        - hidden_level_list
        """)
        
        uploaded_file_conf = st.file_uploader(
            "选择配置文件",
            type=['xlsx', 'xls'],
            key="conf_uploader",
            help="上传包含level_conf和level_group两个sheet的文件"
        )
        
        if uploaded_file_conf:
            st.session_state.uploaded_files['conf'] = uploaded_file_conf
            st.markdown(f'<div class="success-box">✅ 已上传: {uploaded_file_conf.name}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 检查是否两个文件都已上传
    if all(st.session_state.uploaded_files.values()):
        if st.button("下一步：数据验证", type="primary", use_container_width=True):
            try:
                # 读取文件
                df_raw, df_level_conf, df_level_group = read_uploaded_files(
                    st.session_state.uploaded_files['raw'],
                    st.session_state.uploaded_files['conf']
                )
                
                # 保存到session state
                st.session_state.dataframes['df_raw'] = df_raw
                st.session_state.dataframes['df_level_conf'] = df_level_conf
                st.session_state.dataframes['df_level_group'] = df_level_group
                
                # 转到下一步
                st.session_state.step = 2
                st.rerun()
                
            except Exception as e:
                st.error(f"读取文件失败: {str(e)}")
    
    # 显示示例数据预览
    if st.session_state.uploaded_files['raw']:
        with st.expander("📊 原始数据预览"):
            try:
                df_preview = pd.read_excel(st.session_state.uploaded_files['raw'], nrows=5)
                st.dataframe(df_preview)
                st.caption(f"显示前5行，共{len(pd.read_excel(st.session_state.uploaded_files['raw']))}行")
            except:
                pass

# 步骤2: 数据验证
def step_validation():
    """步骤2: 数据验证"""
    st.markdown('<h1 class="main-header">🔍 数据验证</h1>', unsafe_allow_html=True)
    
    if st.session_state.dataframes['df_raw'] is None:
        st.warning("请先上传文件！")
        st.session_state.step = 1
        st.rerun()
        return
    
    # 执行数据验证
    validation_results = validate_dataframes(
        st.session_state.dataframes['df_raw'],
        st.session_state.dataframes['df_level_conf'],
        st.session_state.dataframes['df_level_group']
    )
    
    st.session_state.validation = validation_results
    
    # 显示验证结果
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if validation_results['df_raw_valid']:
            st.markdown('<div class="success-box">✅ 原始数据验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-box">❌ 原始数据缺少列</div>', unsafe_allow_html=True)
            st.write(f"缺少列: {validation_results['missing_columns']['df_raw']}")
    
    with col2:
        if validation_results['df_level_conf_valid']:
            st.markdown('<div class="success-box">✅ level_conf验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-box">❌ level_conf缺少列</div>', unsafe_allow_html=True)
            st.write(f"缺少列: {validation_results['missing_columns']['df_level_conf']}")
    
    with col3:
        if validation_results['df_level_group_valid']:
            st.markdown('<div class="success-box">✅ level_group验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-box">❌ level_group缺少列</div>', unsafe_allow_html=True)
            st.write(f"缺少列: {validation_results['missing_columns']['df_level_group']}")
    
    # 显示数据概览
    st.markdown("### 📊 数据概览")
    
    overview_col1, overview_col2, overview_col3 = st.columns(3)
    
    with overview_col1:
        st.metric("原始数据", 
                 f"{len(st.session_state.dataframes['df_raw'])}行", 
                 f"{len(st.session_state.dataframes['df_raw'].columns)}列")
    
    with overview_col2:
        st.metric("level_conf", 
                 f"{len(st.session_state.dataframes['df_level_conf'])}行", 
                 f"{len(st.session_state.dataframes['df_level_conf'].columns)}列")
    
    with overview_col3:
        st.metric("level_group", 
                 f"{len(st.session_state.dataframes['df_level_group'])}行", 
                 f"{len(st.session_state.dataframes['df_level_group'].columns)}列")
    
    # 导航按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("上一步：重新上传", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    
    with col2:
        if all([validation_results['df_raw_valid'], 
                validation_results['df_level_conf_valid'], 
                validation_results['df_level_group_valid']]):
            if st.button("下一步：开始处理", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()
        else:
            st.button("下一步：开始处理", disabled=True, use_container_width=True)

# 步骤3: 数据处理
def step_processing():
    """步骤3: 数据处理"""
    st.markdown('<h1 class="main-header">🔧 数据处理</h1>', unsafe_allow_html=True)
    
    # 创建进度指示器
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 开始数据处理...")
        progress_bar.progress(10)
        
        # 运行数据处理流水线
        df_processed, df_level_conf_processed, df_level_group_processed = run_full_pipeline(
            st.session_state.dataframes['df_raw'],
            st.session_state.dataframes['df_level_conf'],
            st.session_state.dataframes['df_level_group']
        )
        
        progress_bar.progress(50)
        status_text.text("💾 保存处理结果...")
        
        # 生成Excel文件
        result_bytes = generate_excel_output(df_level_conf_processed, df_level_group_processed)
        
        progress_bar.progress(80)
        
        # 保存处理结果到session state
        st.session_state.processed_data = {
            'df_processed': df_processed,
            'df_level_conf_processed': df_level_conf_processed,
            'df_level_group_processed': df_level_group_processed
        }
        
        st.session_state.result_file = result_bytes
        st.session_state.processing_error = None
        
        progress_bar.progress(100)
        status_text.text("✅ 处理完成！")
        
        # 显示成功消息
        st.success("数据处理成功完成！")
        
        # 自动转到下一步
        st.session_state.step = 4
        st.rerun()
        
    except Exception as e:
        st.session_state.processing_error = str(e)
        st.error(f"处理过程中出错: {str(e)}")
        st.exception(e)
        
        if st.button("重试", type="secondary"):
            st.rerun()

# 步骤4: 结果下载
def step_download():
    """步骤4: 结果下载"""
    st.markdown('<h1 class="main-header">📥 下载结果</h1>', unsafe_allow_html=True)
    
    if st.session_state.result_file is None:
        st.warning("没有处理结果可下载。请返回上一步处理数据。")
        
        if st.button("返回处理步骤", type="primary"):
            st.session_state.step = 3
            st.rerun()
        
        return
    
    # 生成文件名
    filename = generate_filename()
    
    # 下载按钮
    st.download_button(
        label="📥 下载结果文件",
        data=st.session_state.result_file,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="下载包含level_conf和level_group两个sheet的Excel文件"
    )
    
    # 显示处理结果统计
    st.markdown("### 📊 处理结果统计")
    
    if st.session_state.processed_data:
        df_processed = st.session_state.processed_data['df_processed']
        df_level_conf_processed = st.session_state.processed_data['df_level_conf_processed']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("原始数据行数", len(st.session_state.dataframes['df_raw']))
        
        with col2:
            st.metric("处理后数据行数", len(df_processed))
        
        with col3:
            level_name_matched = df_processed['level_name'].notna().sum()
            st.metric("level_name匹配", f"{level_name_matched}/{len(df_processed)}")
        
        with col4:
            evaluation_matched = df_processed['evaluation'].notna().sum()
            st.metric("evaluation计算", f"{evaluation_matched}/{len(df_processed)}")
    
    # 结果预览
    with st.expander("🔍 结果预览"):
        tab1, tab2, tab3 = st.tabs(["处理后数据", "level_conf", "数据统计"])
        
        with tab1:
            if st.session_state.processed_data:
                df_preview = st.session_state.processed_data['df_processed'].head(10)
                st.dataframe(df_preview, use_container_width=True)
        
        with tab2:
            if st.session_state.processed_data:
                conf_preview = st.session_state.processed_data['df_level_conf_processed'].head(10)
                st.dataframe(conf_preview, use_container_width=True)
        
        with tab3:
            if st.session_state.processed_data:
                df_processed = st.session_state.processed_data['df_processed']
                
                # 显示统计信息
                st.write("**数值列统计:**")
                numeric_cols = df_processed.select_dtypes(include=[np.number]).columns
                for col in numeric_cols[:5]:  # 显示前5个数值列
                    if col in ['churn_rate', 'actual_rev', 'z-score']:
                        st.write(f"{col}: 均值={df_processed[col].mean():.3f}, "
                               f"标准差={df_processed[col].std():.3f}")
    
    # 重新开始按钮
    st.markdown("---")
    if st.button("🔄 开始新的分析", type="secondary", use_container_width=True):
        # 重置session state
        for key in ['uploaded_files', 'dataframes', 'validation', 
                   'processed_data', 'result_file', 'processing_error']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.step = 1
        st.rerun()

# 主应用
def main():
    """主应用入口"""
    init_session_state()
    render_sidebar()
    
    # 显示步骤指示器
    steps = ["上传文件", "数据验证", "数据处理", "下载结果"]
    step_html = '<div class="step-indicator">'
    for i, step in enumerate(steps, 1):
        if i == st.session_state.step:
            step_html += f'<div class="step active">步骤{i}: {step}</div>'
        elif i < st.session_state.step:
            step_html += f'<div class="step completed">步骤{i}: {step}</div>'
        else:
            step_html += f'<div class="step">步骤{i}: {step}</div>'
    step_html += '</div>'
    st.markdown(step_html, unsafe_allow_html=True)
    
    # 根据当前步骤显示对应内容
    if st.session_state.step == 1:
        step_upload()
    elif st.session_state.step == 2:
        step_validation()
    elif st.session_state.step == 3:
        step_processing()
    elif st.session_state.step == 4:
        step_download()
    
    # 页脚
    st.markdown("---")
    st.caption("🎮 游戏关卡数据分析工具 v1.0 | 数据仅供内部使用")

if __name__ == "__main__":
    main()