import streamlit as st

from utils.style_utils import load_custom_css

# 加载自定义CSS
load_custom_css()

st.set_page_config(
    page_title="游戏关卡分析工具",
    page_icon="⚙️",
    layout="wide"
)

st.title("🎮 游戏关卡数据分析平台")
st.markdown("请从左侧边栏选择功能模块")

# 显示各模块简介
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 关卡评估")

with col2:
    st.markdown("### 🎯 模拟分析")

with col3:
    st.markdown("### 🔍 配置表完整性检查")

st.markdown("---")
st.caption("游戏关卡数据分析工具 | 数据仅供内部使用")
