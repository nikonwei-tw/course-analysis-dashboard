import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# --- 網頁配置 ---
st.set_page_config(page_title="跨學年課程大數據分析平台", layout="wide")

# --- 資料讀取函數 ---
@st.cache_data
def load_and_combine_data():
    all_dfs = []
    # 搜尋目前目錄下所有 .xlsx 檔案
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    
    if not files:
        return None, [], [], [], []

    for f in files:
        match = re.search(r'(\d{3})-(\d)', f)
        if match:
            year = match.group(1)
            term = match.group(2)
            try:
                temp_df = pd.read_excel(f)
                temp_df['學年度'] = year
                temp_df['學期'] = term
                all_dfs.append(temp_df)
            except Exception as e:
                st.warning(f"檔案 {f} 讀取失敗: {e}")

    if not all_dfs:
        return None, [], [], [], []

    df = pd.concat(all_dfs, ignore_index=True)
    
    # --- 預處理資料 ---
    df['課程標籤'] = df['課程標籤'].fillna('').astype(str)
    all_tags = df['課程標籤'].str.split('\n').explode().str.strip()
    unique_tags = sorted([t for t in all_tags.unique() if t and t.strip()])
    
    # 提取學院與系所清單
    unique_colleges = sorted(df['主開學院名稱_中文'].dropna().unique().tolist())
    unique_depts = sorted(df['主開系所名稱_中文'].dropna().unique().tolist())
    unique_years = sorted(df['學年度'].unique().tolist())
    
    return df, unique_tags, unique_colleges, unique_depts, unique_years

# --- 主程式 ---
try:
    df, tags_list, college_list, dept_list, year_list = load_and_combine_data()

    if df is not None:
        st.title("🎓 跨學年課程數據分析與比較平台")

        # --- 側邊欄：多功能篩選區 ---
        st.sidebar.header("🔍 篩選與比較維度")
        
        selected_years = st.sidebar.multiselect("選擇學年度", options=year_list, default=year_list[-1:])
        selected_terms = st.sidebar.multiselect("選擇學期", options=['1', '2'], default=['1', '2'])

        # 1. 學院篩選
        selected_colleges = st.sidebar.multiselect("篩選學院", options=college_list)
        
        # 2. 系所篩選 (連動建議：如果選了學院，這裡可以只顯示該學院的系所)
        available_depts = dept_list
        if selected_colleges:
            available_depts = sorted(df[df['主開學院名稱_中文'].isin(selected_colleges)]['主開系所名稱_中文'].unique().tolist())
        
        selected_depts = st.sidebar.multiselect("篩選系所", options=available_depts)

        # 3. 標籤與關鍵字
        selected_tags = st.sidebar.multiselect("篩選課程標籤", options=tags_list)
        search_keyword = st.sidebar.text_input("搜尋課程名稱", "")

        # --- 執行資料過濾 ---
        f_df = df.copy()
        f_df = f_df[(f_df['學年度'].isin(selected_years)) & (f_df['學期'].isin(selected_terms))]
        
        if selected_colleges:
            f_df = f_df[f_df['主開學院名稱_中文'].isin(selected_colleges)]
        
        if selected_depts:
            f_df = f_df[f_df['主開系所名稱_中文'].isin(selected_depts)]
        
        if selected_tags:
            mask = f_df['課程標籤'].apply(lambda x: any(tag in x for tag in selected_tags))
            f_df = f_df[mask]
            
        if search_keyword:
            f_df = f_df[f_df['主開科目名稱'].str.contains(search_keyword, na=False, case=False)]

        # --- 數據呈現區 ---
        unique_courses_df = f_df.drop_duplicates(subset=['學年度', '學期', '主開課程碼'])
        total_unique = len(unique_courses_df)
        
        st.divider()
        st.metric("符合條件的總開課數", f"{total_unique} 門")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📅 年度/學期開課數比較")
            stats_trend = unique_courses_df.groupby(['學年度', '學期']).size().reset_index(name='課程數')
            stats_trend['學期別'] = stats_trend['學年度'] + "-" + stats_trend['學期']
            fig_bar = px.bar(stats_trend, x='學期別', y='課程數', color='學年度', text='課程數', barmode='group')
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.subheader("🏛️ 系所開課佔比")
            # 改為顯示系所的分佈
            stats_dept = unique_courses_df.groupby('主開系所名稱_中文').size().reset_index(name='課程數')
            stats_dept = stats_dept.sort_values('課程數', ascending=False).head(20) # 只顯示前20大系所避免圖表太亂
            fig_pie = px.pie(stats_dept, values='課程數', names='主開系所名稱_中文', hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.subheader("📋 課程詳細清單")
        display_cols = ['學年度', '學期', '主開學院名稱_中文', '主開系所名稱_中文', '主開課程碼', '主開科目名稱', '課程標籤']
        st.dataframe(unique_courses_df[display_cols].reset_index(drop=True), use_container_width=True)

    else:
        st.warning("請在 GitHub 中上傳命名格式為 '114-1.xlsx' 的檔案。")

except Exception as e:
    st.error(f"系統運行錯誤: {e}")