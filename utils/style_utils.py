# utils/style_utils.py
import streamlit as st
import os

def load_custom_css():
    """加载自定义CSS样式"""
    css_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'custom.css')
    
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # 如果CSS文件不存在，使用内联CSS
        st.markdown("""
        <style>
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {
                font-size: 1.5rem !important;
            }
            
            [data-testid="stSidebar"] * {
                font-size: 1.1rem !important;
            }
        </style>
        """, unsafe_allow_html=True)
