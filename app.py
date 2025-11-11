import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import os

from llm_utils import analyze_call_with_llm, generate_product_insights
from config import LLM_CONFIG
from sheet_utils import get_google_sheet_data

st.set_page_config(
    page_title="LLM• Анализ звонков для продуктовых инсайтов",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
    .success-box { padding: 1rem; border-radius: 0.5rem; background-color: #d4edda; border: 1px solid #c3e6cb; margin: 1rem 0; }
    .insight-box { background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; margin: 0.5rem 0; }
    .product-insight { background-color: #e8f4fd; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #ff6b6b; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<div class="main-header">Product Insights • Анализ звонков</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Настройки")
        llm_provider = st.selectbox("Нейросеть:", ["Yandex GPT", "GigaChat"])
        sheet_url = st.text_input("URL Google Таблицы:", value=st.session_state.get('sheet_url', ''))
        if sheet_url:
            st.session_state.sheet_url = sheet_url

    tab1, tab2 = st.tabs(["Анализ звонка", "Просмотр инсайтов"])

    with tab1:
        st.subheader("Ручной анализ звонка")
        call_text = st.text_area("Введите текст звонка:", height=200)

        if st.button("Проанализировать", type="primary") and call_text.strip():
            with st.spinner("Анализируем..."):
                analysis = analyze_call_with_llm(call_text)
                if analysis:
                    insights = generate_product_insights(analysis)
                    display_results(analysis, insights)

    with tab2:
        st.subheader("Просмотр продуктовых инсайтов")
        if st.button("Обновить данные"):
            if st.session_state.get('sheet_url'):
                feed_data = get_google_sheet_data(st.session_state.sheet_url)
                if feed_data:
                    df = pd.DataFrame(feed_data)
                    st.dataframe(df)


def display_results(analysis, insights):
    st.success("✅ Анализ завершен!")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Анализ обращения")
        st.markdown(f'<div class="insight-box">**Проблема:** {analysis.get("main_problem")}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">**Страх:** {analysis.get("key_fear")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">**Решение:** {analysis.get("result_solution")}</div>',
                    unsafe_allow_html=True)

        st.write("**Цитаты:**")
        for phrase in analysis.get("original_phrases", []):
            st.code(phrase)

    with col2:
        st.subheader("Продуктовые инсайты")
        if insights:
            # Отображаем продуктовые инсайты
            product_insights = insights.get("product_insights", [])
            if product_insights:
                for insight in product_insights:
                    st.markdown(f'<div class="product-insight">{insight}</div>', unsafe_allow_html=True)

            # Отображаем предложения по фичам
            feature_suggestions = insights.get("feature_suggestions", [])
            if feature_suggestions:
                st.write("**Предложения:**")
                for feature in feature_suggestions:
                    st.write(f"• {feature}")
        else:
            st.info("Инсайты не сгенерированы")


if __name__ == "__main__":
    main()
