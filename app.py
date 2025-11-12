import os
from datetime import datetime

import pandas as pd
import streamlit as st

from llm_utils import analyze_call_with_llm, generate_product_insights
from sheet_utils import get_google_sheet_data

st.set_page_config(page_title="LLM• Анализ звонков", page_icon="📊", layout="wide")
st.markdown("""
<style>
.main-header{font-size:2.5rem;color:#1f77b4;text-align:center;margin-bottom:2rem}
.success-box{padding:1rem;border-radius:.5rem;background:#d4edda;border:1px solid #c3e6cb;margin:1rem 0}
.insight-box{background:#f8f9fa;padding:1rem;border-radius:.5rem;border-left:4px solid #1f77b4;margin:.5rem 0}
.product-insight{background:#e8f4fd;padding:1rem;border-radius:.5rem;border-left:4px solid #ff6b6b;margin:.5rem 0}
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header">Product Insights • Анализ звонков</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Настройки")
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
                else:
                    st.error("Не удалось получить анализ. Проверьте ключи ЯндексGPT.")

    with tab2:
        st.subheader("Просмотр продуктовых инсайтов")
        if st.button("Обновить данные"):
            url = st.session_state.get('sheet_url')
            if url:
                feed_data = get_google_sheet_data(url)
                if feed_data:
                    df = pd.DataFrame(feed_data)
                    st.dataframe(df, use_container_width=True)

def display_results(analysis, insights):
    st.success("✅ Анализ завершен!")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Анализ обращения")
        st.markdown(f'<div class="insight-box"><b>Проблема:</b> {analysis.get("main_problem","")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box"><b>Страх:</b> {analysis.get("key_fear","")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box"><b>Результат:</b> {analysis.get("result_solution","")}</div>', unsafe_allow_html=True)
        st.write("**Цитаты:**")
        for p in analysis.get("original_phrases", []):
            st.code(p)
    with col2:
        st.subheader("Продуктовые инсайты")
        if not insights:
            st.info("Инсайты не сгенерированы")
            return
        for i in (insights.get("product_insights") or []):
            st.markdown(f'<div class="product-insight">{i}</div>', unsafe_allow_html=True)
        feats = insights.get("feature_suggestions") or []
        if feats:
            st.write("**Предложения:**")
            for f in feats:
                st.write(f"• {f}")

if __name__ == "__main__":
    main()
