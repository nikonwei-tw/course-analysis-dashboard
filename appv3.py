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
    df['課程標籤'] = df['課程標籤'].fillna('').astype(str)
    all_tags = df['課程標籤'].str.split('\n').explode().str.strip()
    unique_tags = sorted([t for t in all_tags.unique() if t and t.strip()])
    unique_colleges = sorted(df['主開學院名稱_中文'].dropna().unique().tolist())
    unique_depts = sorted(df['主開系所名稱_中文'].dropna().unique().tolist())
    unique_years = sorted(df['學年度'].unique().tolist())
    
    return df, unique_tags, unique_colleges, unique_depts, unique_years

# --- 主程式 ---
try:
    df, tags_list, college_list, dept_list, year_list = load_and_combine_data()

    if df is not None:
        st.title("🎓 跨學年課程數據分析平台")

        # --- 側邊欄：全方塊化篩選區 ---
        st.sidebar.header("🔧 篩選工具箱")
        
        st.sidebar.write("##### 學年度")
        selected_years = st.sidebar.pills("選擇年度：", options=year_list, selection_mode="multi", default=year_list[-1:])
        
        st.sidebar.write("##### 學期")
        selected_terms = st.sidebar.pills("選擇學期：", options=['1', '2'], selection_mode="multi", default=['1', '2'])

        st.sidebar.write("##### 學院類別")
        selected_colleges = st.sidebar.pills("選擇學院：", options=college_list, selection_mode="multi")
        
        st.sidebar.write("##### 課程標籤")
        selected_tags = st.sidebar.pills("選擇標籤：", options=tags_list, selection_mode="multi")

        st.sidebar.divider()

        available_depts = dept_list
        if selected_colleges:
            available_depts = sorted(df[df['主開學院名稱_中文'].isin(selected_colleges)]['主開系所名稱_中文'].unique().tolist())
        
        selected_depts = st.sidebar.multiselect("特定系所篩選", options=available_depts)
        search_keyword = st.sidebar.text_input("搜尋課程名稱關鍵字", "")

        # --- 執行資料過濾 ---
        f_df = df.copy()
        f_df = f_df[(f_df['學年度'].isin(selected_years or [])) & (f_df['學期'].isin(selected_terms or []))]
        
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
        st.metric("當前條件下總開課數", f"{total_unique} 門")

        # --- 圖表區 (改為兩列顯示三圖) ---
        if not unique_courses_df.empty:
            # 第一列：趨勢圖與學院圓餅圖
            row1_col1, row1_col2 = st.columns([1, 1])
            
            with row1_col1:
                st.subheader("📅 歷年開課趨勢比較")
                stats_trend = unique_courses_df.groupby(['學年度', '學期']).size().reset_index(name='課程數')
                stats_trend['學期別'] = stats_trend['學年度'] + "-" + stats_trend['學期']
                fig_trend = px.line(stats_trend, x='學期別', y='課程數', markers=True, text='課程數')
                st.plotly_chart(fig_trend, use_container_width=True)

            with row1_col2:
                st.subheader("🏛️ 各學院開課佔比")
                stats_college = unique_courses_df.groupby('主開學院名稱_中文').size().reset_index(name='課程數')
                fig_pie = px.pie(stats_college, values='課程數', names='主開學院名稱_中文', hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)

            # 第二列：學院長條圖與系所 Top 15
            row2_col1, row2_col2 = st.columns([1, 1])
            
            with row2_col1:
                st.subheader("📊 各學院開課數量")
                stats_college_bar = stats_college.sort_values('課程數', ascending=True)
                fig_col_bar = px.bar(stats_college_bar, y='主開學院名稱_中文', x='課程數', 
                                     orientation='h', text='課程數', color='課程數',
                                     color_continuous_scale='Blues')
                st.plotly_chart(fig_col_bar, use_container_width=True)

            with row2_col2:
                st.subheader("🏫 系所開課 Top 15")
                stats_dept = unique_courses_df.groupby('主開系所名稱_中文').size().reset_index(name='課程數')
                stats_dept = stats_dept.sort_values('課程數', ascending=False).head(15)
                fig_dept_bar = px.bar(stats_dept, x='課程數', y='主開系所名稱_中文', 
                                      orientation='h', text='課程數',
                                      color_discrete_sequence=['#FFA15A'])
                st.plotly_chart(fig_dept_bar, use_container_width=True)
        else:
            st.info("請選擇篩選條件以顯示圖表")

        st.divider()
        st.subheader("📋 課程詳細清單")
        display_cols = ['學年度', '學期', '主開學院名稱_中文', '主開系所名稱_中文', '主開課程碼', '主開科目名稱', '課程標籤']
        st.dataframe(unique_courses_df[display_cols].reset_index(drop=True), use_container_width=True)

    else:
        st.warning("請在目錄中放置 Excel 檔案。")

except Exception as e:
    st.error(f"系統運行錯誤: {e}")