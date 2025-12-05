"""
关卡评估页面 - 完整功能
分析关卡表现，生成评估结果和推荐难度
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享常量 🔥 现在从config导入
from config import FUUU_NEW, FUUU_OLD, FUUU_EVA, ATTRIBUTE_MAP, PROCESSING_CONFIG

# 导入数据处理函数
from utils.data_processing import run_full_pipeline
from utils.file_utils import (
    read_uploaded_files,
    validate_dataframes,
    generate_excel_output,
    generate_filename
)
from utils.style_utils import load_custom_css

# 加载自定义CSS
load_custom_css()

# 页面配置
st.set_page_config(
    page_title="关卡评估",
    page_icon="📊",
    layout="wide"
)

# ==============================
# Session State初始化
# ==============================
def init_eval_session():
    """初始化关卡评估的session state"""
    # 处理步骤
    if 'eval_step' not in st.session_state:
        st.session_state.eval_step = 1  # 1:上传, 2:验证, 3:处理, 4:下载
    
    # 上传的文件
    if 'eval_uploaded_files' not in st.session_state:
        st.session_state.eval_uploaded_files = {
            'raw': None,
            'conf': None
        }
    
    # 数据框
    if 'eval_dataframes' not in st.session_state:
        st.session_state.eval_dataframes = {
            'df_raw': None,
            'df_level_conf': None,
            'df_level_group': None
        }
    
    # 验证结果
    if 'eval_validation' not in st.session_state:
        st.session_state.eval_validation = None
    
    # 处理后的数据
    if 'eval_processed_data' not in st.session_state:
        st.session_state.eval_processed_data = None
    
    # 结果文件
    if 'eval_result_file' not in st.session_state:
        st.session_state.eval_result_file = None
    
    # 处理错误
    if 'eval_processing_error' not in st.session_state:
        st.session_state.eval_processing_error = None
    
    # 处理进度
    if 'eval_progress' not in st.session_state:
        st.session_state.eval_progress = 0
    
    # 使用共享配置中的默认值 🔥
    if 'zscore_threshold' not in st.session_state:
        st.session_state.zscore_threshold = PROCESSING_CONFIG['default_zscore_threshold']
    
    if 'outlier_threshold' not in st.session_state:
        st.session_state.outlier_threshold = PROCESSING_CONFIG['default_outlier_threshold']

# ==============================
# 页面布局组件
# ==============================
def show_eval_steps():
    """显示关卡评估的步骤指示器"""
    steps = [
        ("📁 文件上传", "上传原始数据和配置文件"),
        ("🔍 数据验证", "检查数据格式和完整性"),
        ("🔧 数据处理", "执行分析计算"),
        ("📥 下载结果", "获取分析结果文件")
    ]
    
    # 创建步骤指示器
    st.markdown("### 处理流程")
    
    cols = st.columns(len(steps))
    for i, (step_title, step_desc) in enumerate(steps, 1):
        with cols[i-1]:
            if i == st.session_state.eval_step:
                st.markdown(f"<div style='background-color: #1E88E5; color: white; padding: 10px; border-radius: 5px; text-align: center;'>"
                          f"<b>步骤{i}</b><br>{step_title}</div>", 
                          unsafe_allow_html=True)
            elif i < st.session_state.eval_step:
                st.markdown(f"<div style='background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px; text-align: center;'>"
                          f"<b>步骤{i}</b><br>{step_title}</div>", 
                          unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;'>"
                          f"<b>步骤{i}</b><br>{step_title}</div>", 
                          unsafe_allow_html=True)
    
    st.markdown("---")

# ==============================
# 步骤1: 文件上传
# ==============================
def upload_section():
    """文件上传部分"""
    st.header("📁 数据上传")
    
    st.markdown("""
    **📝 上传说明：**
    - **原始数据文件**: 包含玩家行为数据的Excel文件
    - **配置文件**: 包含level_conf和level_group两个sheet的Excel文件
    - 支持 `.xlsx` 和 `.xls` 格式
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 原始数据文件")
        uploaded_file_raw = st.file_uploader(
            "选择原始数据文件",
            type=['xlsx', 'xls'],
            key="eval_raw_uploader",
            help="上传events_level_raw.xlsx类似的文件"
        )
        
        if uploaded_file_raw:
            st.session_state.eval_uploaded_files['raw'] = uploaded_file_raw
            st.success(f"✅ 已上传: {uploaded_file_raw.name}")
            
            # 预览原始数据
            with st.expander("📊 原始数据预览"):
                try:
                    df_preview = pd.read_excel(uploaded_file_raw, nrows=5)
                    st.dataframe(df_preview)
                    st.caption(f"文件大小: {uploaded_file_raw.size / 1024:.1f} KB | 显示前5行")
                except Exception as e:
                    st.warning(f"预览失败: {str(e)}")
    
    with col2:
        st.subheader("2. 配置文件")
        uploaded_file_conf = st.file_uploader(
            "选择配置文件",
            type=['xlsx', 'xls'],
            key="eval_conf_uploader",
            help="上传包含level_conf和level_group两个sheet的文件"
        )
        
        if uploaded_file_conf:
            st.session_state.eval_uploaded_files['conf'] = uploaded_file_conf
            st.success(f"✅ 已上传: {uploaded_file_conf.name}")
            
            # 预览配置文件
            with st.expander("📋 配置文件预览"):
                try:
                    # 尝试读取两个sheet
                    xls = pd.ExcelFile(uploaded_file_conf)
                    sheet_names = xls.sheet_names
                    st.write(f"包含Sheet: {', '.join(sheet_names)}")
                    
                    if 'level_conf' in sheet_names:
                        df_conf_preview = pd.read_excel(uploaded_file_conf, sheet_name='level_conf', nrows=5)
                        st.write("**level_conf预览:**")
                        st.dataframe(df_conf_preview)
                    
                    if 'level_group' in sheet_names:
                        df_group_preview = pd.read_excel(uploaded_file_conf, sheet_name='level_group', nrows=5)
                        st.write("**level_group预览:**")
                        st.dataframe(df_group_preview)
                        
                except Exception as e:
                    st.warning(f"预览失败: {str(e)}")
    
    # 检查是否两个文件都已上传
    all_uploaded = all(st.session_state.eval_uploaded_files.values())
    
    # 导航按钮
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("🔄 重置", help="清除所有上传的文件", use_container_width=True):
            reset_evaluation()
    
    with col2:
        if all_uploaded:
            if st.button("下一步：数据验证 →", type="primary", use_container_width=True):
                try:
                    # 读取文件
                    df_raw, df_level_conf, df_level_group = read_uploaded_files(
                        st.session_state.eval_uploaded_files['raw'],
                        st.session_state.eval_uploaded_files['conf']
                    )
                    
                    # 保存到session state
                    st.session_state.eval_dataframes['df_raw'] = df_raw
                    st.session_state.eval_dataframes['df_level_conf'] = df_level_conf
                    st.session_state.eval_dataframes['df_level_group'] = df_level_group
                    
                    # 转到下一步
                    st.session_state.eval_step = 2
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 读取文件失败: {str(e)}")
        else:
            st.button("下一步：数据验证 →", disabled=True, use_container_width=True,
                     help="请先上传两个文件")

# ==============================
# 步骤2: 数据验证
# ==============================
def validation_section():
    """数据验证部分"""
    st.header("🔍 数据验证")
    
    if st.session_state.eval_dataframes['df_raw'] is None:
        st.warning("数据未加载，请返回上一步重新上传文件")
        if st.button("返回文件上传"):
            st.session_state.eval_step = 1
            st.rerun()
        return
    
    # 执行数据验证
    with st.spinner("正在验证数据..."):
        validation_results = validate_dataframes(
            st.session_state.eval_dataframes['df_raw'],
            st.session_state.eval_dataframes['df_level_conf'],
            st.session_state.eval_dataframes['df_level_group']
        )
    
    st.session_state.eval_validation = validation_results
    
    # 显示验证结果
    st.subheader("✅ 验证结果")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if validation_results['df_raw_valid']:
            st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; text-align: center;">'
                       '<h3>✅</h3><b>原始数据</b><br>验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; text-align: center;">'
                       '<h3>❌</h3><b>原始数据</b><br>验证失败</div>', unsafe_allow_html=True)
            st.error(f"缺少列: {validation_results['missing_columns']['df_raw']}")
    
    with col2:
        if validation_results['df_level_conf_valid']:
            st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; text-align: center;">'
                       '<h3>✅</h3><b>level_conf</b><br>验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; text-align: center;">'
                       '<h3>❌</h3><b>level_conf</b><br>验证失败</div>', unsafe_allow_html=True)
            st.error(f"缺少列: {validation_results['missing_columns']['df_level_conf']}")
    
    with col3:
        if validation_results['df_level_group_valid']:
            st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; text-align: center;">'
                       '<h3>✅</h3><b>level_group</b><br>验证通过</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; text-align: center;">'
                       '<h3>❌</h3><b>level_group</b><br>验证失败</div>', unsafe_allow_html=True)
            st.error(f"缺少列: {validation_results['missing_columns']['df_level_group']}")
    
    # 显示数据概览
    st.subheader("📊 数据概览")
    
    overview_col1, overview_col2, overview_col3 = st.columns(3)
    
    with overview_col1:
        df_raw = st.session_state.eval_dataframes['df_raw']
        st.metric("原始数据", 
                 f"{len(df_raw):,} 行", 
                 f"{len(df_raw.columns)} 列")
        
        with st.expander("原始数据列名"):
            st.write(", ".join(df_raw.columns.tolist()))
    
    with overview_col2:
        df_level_conf = st.session_state.eval_dataframes['df_level_conf']
        st.metric("level_conf", 
                 f"{len(df_level_conf):,} 行", 
                 f"{len(df_level_conf.columns)} 列")
    
    with overview_col3:
        df_level_group = st.session_state.eval_dataframes['df_level_group']
        st.metric("level_group", 
                 f"{len(df_level_group):,} 行", 
                 f"{len(df_level_group.columns)} 列")
    
    # 导航按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← 上一步：重新上传", use_container_width=True):
            st.session_state.eval_step = 1
            st.rerun()
    
    with col2:
        if all([validation_results['df_raw_valid'], 
                validation_results['df_level_conf_valid'], 
                validation_results['df_level_group_valid']]):
            if st.button("下一步：开始处理 →", type="primary", use_container_width=True):
                st.session_state.eval_step = 3
                st.rerun()
        else:
            st.button("下一步：开始处理 →", disabled=True, use_container_width=True,
                     help="请先解决数据验证问题")

# ==============================
# 步骤3: 数据处理
# ==============================
def processing_section():
    """数据处理部分"""
    st.header("🔧 数据处理")
    
    st.markdown("""
    **🔄 处理流程包括：**
    1. Level Name匹配
    2. Churn Rate计算  
    3. Revenue计算
    4. Actual Revenue计算
    5. Z-Score计算
    6. Evaluation评估
    7. 属性提取
    8. 难度推荐
    """)
    
    # 处理参数配置
    with st.expander("⚙️ 处理参数配置"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.zscore_threshold = st.slider(
                "Z-score阈值",
                min_value=0.5,
                max_value=3.0,
                value=st.session_state.zscore_threshold,
                step=0.1,
                help="用于确定evaluation的z-score阈值"
            )
        with col2:
            st.session_state.outlier_threshold = st.slider(
                "异常值阈值",
                min_value=100,
                max_value=500,
                value=st.session_state.outlier_threshold,
                step=50,
                help="actual_rev异常值过滤阈值"
            )
    
    # 开始处理按钮
    if st.button("🚀 开始数据处理", type="primary", use_container_width=True):
        process_data()
    
    # 显示处理进度（如果有）
    if st.session_state.eval_progress > 0:
        progress_bar = st.progress(st.session_state.eval_progress)
        st.write(f"处理进度: {st.session_state.eval_progress}%")
    
    # 导航按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← 上一步：数据验证", use_container_width=True):
            st.session_state.eval_step = 2
            st.rerun()

def process_data():
    """执行数据处理"""
    try:
        # 创建进度指示器
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        # 更新进度
        progress_placeholder.text("🔄 开始数据处理...")
        progress_bar.progress(10)
        
        # 运行完整的数据处理流水线
        df_processed, df_level_conf_processed, df_level_group_processed = run_full_pipeline(
            st.session_state.eval_dataframes['df_raw'],
            st.session_state.eval_dataframes['df_level_conf'],
            st.session_state.eval_dataframes['df_level_group']
        )
        
        progress_bar.progress(50)
        progress_placeholder.text("💾 保存处理结果...")
        
        # 生成Excel文件
        result_bytes = generate_excel_output(df_level_conf_processed, df_level_group_processed)
        
        progress_bar.progress(80)
        
        # 保存处理结果到session state
        st.session_state.eval_processed_data = {
            'df_processed': df_processed,
            'df_level_conf_processed': df_level_conf_processed,
            'df_level_group_processed': df_level_group_processed
        }
        
        st.session_state.eval_result_file = result_bytes
        st.session_state.eval_processing_error = None
        
        progress_bar.progress(100)
        progress_placeholder.text("✅ 处理完成！")
        
        # 显示成功消息
        st.success("✅ 数据处理成功完成！")
        
        # 显示处理结果统计
        show_processing_stats(df_processed, df_level_conf_processed)
        
        # 自动转到下一步
        st.session_state.eval_step = 4
        st.rerun()
        
    except Exception as e:
        st.session_state.eval_processing_error = str(e)
        st.error(f"❌ 处理过程中出错: {str(e)}")
        st.exception(e)

def show_processing_stats(df_processed, df_level_conf_processed):
    """显示处理结果统计"""
    st.subheader("📈 处理结果统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        level_name_matched = df_processed['level_name'].notna().sum()
        total_rows = len(df_processed)
        st.metric("Level Name匹配", 
                 f"{level_name_matched:,}/{total_rows:,}",
                 f"{level_name_matched/total_rows*100:.1f}%")
    
    with col2:
        evaluation_matched = df_processed['evaluation'].notna().sum()
        st.metric("Evaluation计算", 
                 f"{evaluation_matched:,}/{total_rows:,}",
                 f"{evaluation_matched/total_rows*100:.1f}%")
    
    with col3:
        attribute_count = df_level_conf_processed['attribute'].apply(lambda x: len(str(x).split(',')) if pd.notna(x) and x != '' else 0).sum()
        st.metric("属性提取", 
                 f"{attribute_count:,} 个",
                 f"平均{attribute_count/len(df_level_conf_processed):.1f}个/关卡")
    
    with col4:
        difficulty_count = df_level_conf_processed['rec_difficulty'].apply(lambda x: len(str(x).split(',')) if pd.notna(x) and x != '' else 0).sum()
        st.metric("难度推荐", 
                 f"{difficulty_count:,} 个",
                 f"平均{difficulty_count/len(df_level_conf_processed):.1f}个/关卡")

# ==============================
# 步骤4: 下载结果
# ==============================
def download_section():
    """下载结果部分"""
    st.header("📥 下载结果")
    
    if st.session_state.eval_result_file is None:
        st.warning("没有处理结果可下载。请返回上一步处理数据。")
        
        if st.button("← 返回处理步骤", type="primary"):
            st.session_state.eval_step = 3
            st.rerun()
        
        return
    
    # 生成文件名
    filename = generate_filename()
    
    # 下载按钮
    st.download_button(
        label="📥 下载结果文件",
        data=st.session_state.eval_result_file,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="下载包含level_conf和level_group两个sheet的Excel文件"
    )
    
    # 显示文件信息
    st.info(f"**文件信息**: {filename} | 大小: {len(st.session_state.eval_result_file) / 1024:.1f} KB")
    
    
    # 重新开始按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 开始新的分析", type="secondary", use_container_width=True):
            reset_evaluation()
            st.rerun()
    
    with col2:
        if st.button("← 返回处理步骤", use_container_width=True):
            st.session_state.eval_step = 3
            st.rerun()

# ==============================
# 工具函数
# ==============================
def reset_evaluation():
    """重置关卡评估的状态"""
    st.session_state.eval_step = 1
    st.session_state.eval_uploaded_files = {'raw': None, 'conf': None}
    st.session_state.eval_dataframes = {'df_raw': None, 'df_level_conf': None, 'df_level_group': None}
    st.session_state.eval_validation = None
    st.session_state.eval_processed_data = None
    st.session_state.eval_result_file = None
    st.session_state.eval_processing_error = None
    st.session_state.eval_progress = 0
    # 保留配置参数
    st.session_state.zscore_threshold = PROCESSING_CONFIG['default_zscore_threshold']
    st.session_state.outlier_threshold = PROCESSING_CONFIG['default_outlier_threshold']

# ==============================
# 主函数
# ==============================
def main():
    """关卡评估页面主函数"""
    st.title("📊 关卡评估")
    st.markdown("分析关卡表现，生成评估结果和推荐难度")
    
    # 初始化session state
    init_eval_session()
    
    # 显示处理步骤
    show_eval_steps()
    
    # 根据当前步骤显示对应内容
    if st.session_state.eval_step == 1:
        upload_section()
    elif st.session_state.eval_step == 2:
        validation_section()
    elif st.session_state.eval_step == 3:
        processing_section()
    elif st.session_state.eval_step == 4:
        download_section()
    
    # 页脚
    st.markdown("---")
    st.caption("🎮 游戏关卡数据分析工具 - 关卡评估模块 | 数据仅供内部使用")

# ==============================
# 运行应用
# ==============================
if __name__ == "__main__":
    main()
