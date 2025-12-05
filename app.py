import streamlit as st

# 添加自定义CSS样式
st.markdown("""
<style>
    /* 调整sidebar标题大小 */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 1.5rem !important;
    }
    
    /* 调整sidebar所有文字大小 */
    [data-testid="stSidebar"] * {
        font-size: 1.1rem !important;
    }
    
    /* 只调整sidebar中的标题 */
    [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj {
        font-size: 1.3rem !important;
    }
    
    /* 调整sidebar中的小标题 */
    [data-testid="stSidebar"] .st-emotion-cache-16idsys p {
        font-size: 1.2rem !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

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
