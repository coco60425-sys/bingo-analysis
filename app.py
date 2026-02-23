import streamlit as st
import pandas as pd
import re
import time
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from streamlit_autorefresh import st_autorefresh

# --- 系統設定與色彩 CSS ---
st.set_page_config(page_title="BINGO BINGO 分析系統", layout="wide", page_icon="🌈")

st.markdown("""
<style>
    h1 {
        color: #FF4B4B;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF904F);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    h2 { color: #0068C9; }
    h3 { color: #29B09D; }
    .stButton>button {
        border-radius: 20px;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF904F 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    .stExpander { border: 2px solid #E8F0FE; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🌈 台彩 BINGO BINGO 分析系統 🎰")

# 初始化 session_state
if "history_data" not in st.session_state:
    st.session_state.history_data = pd.DataFrame()

# --- 側邊欄選單 ---
st.sidebar.markdown("<h2 style='color: #8A2BE2;'>📌 系統功能選單</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("請選擇功能", ["基礎與連動率分析", "設定 (準備中)"])

st.sidebar.markdown("---")
# 5 分鐘自動刷新開關
auto_update = st.sidebar.checkbox("🔄 開啟 5 分鐘自動刷新獎號")
if auto_update:
    st_autorefresh(interval=300000, key="bingo_auto_refresh")
    st.sidebar.success("✨ 已開啟自動刷新，每 5 分鐘將自動抓取最新獎號。")

if menu == "基礎與連動率分析":
    
    st.markdown("### 📊 步驟一：抓取最新 4 期開獎數據")
    
    if st.button("🚀 手動刷新獎號 (抓取 4 期)") or auto_update:
        with st.spinner("啟動背景瀏覽器，等待動態數據載入中 (約需 8-10 秒)..."):
            url = "https://lotto.auzonet.com/bingobingo.php"
            driver = None
            
            try:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                driver.get(url)
                time.sleep(8)  # 拉長等待時間確保 JS 完全載入
                
                html_content = driver.page_source
                
                soup = BeautifulSoup(html_content, "html.parser")
                rows = soup.find_all("tr")
                
                parsed_data = []
                seen_issues = set()
                
                for row in rows:
                    # 改回整列讀取，不依賴欄位索引
                    row_text = row.get_text(separator=" ", strip=True)
                    
                    # 1. 找期數
                    issue_match = re.search(r'(11\d{7})', row_text)
                    if not issue_match:
                        continue
                        
                    issue_str = issue_match.group(1)
                    if issue_str in seen_issues:
                        continue
                    
                    # 2. 找時間
                    time_match = re.search(r'(\d{2}:\d{2})', row_text)
                    time_str = time_match.group(1) if time_match else ""
                    
                    # 3. 剃除干擾資訊 (時間、期數、可能出現的日期)
                    clean_text = re.sub(r'\d{2}:\d{2}(:\d{2})?', ' ', row_text)
                    clean_text = re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', ' ', clean_text)
                    clean_text = clean_text.replace(issue_str, ' ')
                    
                    # 4. 抓取號碼
                    raw_nums = re.findall(r'\b\d{1,2}\b', clean_text)
                    valid_nums = [f"{int(n):02d}" for n in raw_nums if 1 <= int(n) <= 80]
                    
                    draw_nums = []
                    for n in valid_nums:
                        if n not in draw_nums and len(draw_nums) < 20:
                            draw_nums.append(n)
                        if len(draw_nums) == 20:
                            break
                            
                    # 5. 嚴格審查：同一列要有 20 個號碼才算有效開獎
                    if len(draw_nums) == 20:
                        parsed_data.append({
                            "開獎期數": issue_str,
                            "開獎時間": time_str,
                            "開獎號碼": ", ".join(draw_nums),
                            "號碼清單": draw_nums
                        })
                        seen_issues.add(issue_str)
                        
                    if len(parsed_data) == 4:
                        break
                
                if parsed_data:
                    st.session_state.history_data = pd.DataFrame(parsed_data)
                    st.success(f"🎉 成功抓取 {len(parsed_data)} 期資料。")
                else:
                    st.error("⚠️ 解析失敗：畫面上未出現符合格式的數據。可能網站載入過慢。")
                    
            except Exception as e:
                st.error(f"🛑 背景瀏覽器執行錯誤：{e}")
            finally:
                if driver:
                    driver.quit()

    df = st.session_state.history_data
    if not df.empty:
        with st.expander("📂 點此展開查看原始 4 期開獎數據"):
            st.dataframe(df[["開獎期數", "開獎時間", "開獎號碼"]], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 建立分析專用的 DataFrame (排除 07:05，並只取最新 3 期)
        df_analysis = df[df["開獎時間"] != "07:05"].head(3)
        st.info("💡 **系統提示**：進入分析階段，已自動排除 `07:05` 的無效期數，並採用剩餘的最新的 **3 期**數據進行精準運算。")
        
        st.markdown("### 📈 步驟二：AB 連動率分析 (目標 > 15%)")
        
        if st.button("🔮 執行連動策略計算"):
            if len(df_analysis) < 2:
                st.warning("⚠️ 排除無效期數後，剩餘資料不足 2 期，無法計算連動率。")
            else:
                df_chrono = df_analysis.iloc[::-1].reset_index(drop=True)
                
                pair_counts = defaultdict(int)
                a_counts = defaultdict(int)
                
                for i in range(len(df_chrono) - 1):
                    current_draw = df_chrono.iloc[i]['號碼清單']
                    next_draw = df_chrono.iloc[i+1]['號碼清單']
                    
                    for a in current_draw:
                        a_counts[a] += 1
                        for b in next_draw:
                            if a != b:
                                pair_counts[(a, b)] += 1
                
                rates = []
                for (a, b), count in pair_counts.items():
                    rate = count / a_counts[a]
                    if rate > 0.15:
                        rates.append({
                            "前導號 (A)": a,
                            "跟隨號 (B)": b,
                            "A 出現總數": a_counts[a],
                            "B 成功跟隨次數": count,
                            "連動率": f"{rate*100:.1f}%",
                            "_sort_rate": rate
                        })
                
                if rates:
                    rates_df = pd.DataFrame(rates)
                    rates_df = rates_df.sort_values(by=["_sort_rate", "B 成功跟隨次數"], ascending=[False, False])
                    
                    top_3_df = rates_df.head(3).drop(columns=["_sort_rate"]).reset_index(drop=True)
                    
                    st.success("✅ **以下為連動率最高的 3 組策略：**")
                    st.dataframe(top_3_df, use_container_width=True)
                    
                    st.markdown("#### 🎯 步驟三：近 3 期策略驗證")
                    latest_3 = df_analysis.head(3).iloc[::-1].reset_index(drop=True)
                    
                    validation_results = []
                    for index, row in top_3_df.iterrows():
                        a_num = row["前導號 (A)"]
                        b_num = row["跟隨號 (B)"]
                        hit_count = 0
                        
                        for i in range(len(latest_3) - 1):
                            curr_draw = latest_3.iloc[i]['號碼清單']
                            nxt_draw = latest_3.iloc[i+1]['號碼清單']
                            
                            if a_num in curr_draw and b_num in nxt_draw:
                                hit_count += 1
                                
                        status = "🔥 近期有發動" if hit_count > 0 else "❄️ 近 3 期未發動"
                        validation_results.append({
                            "策略組合": f"A: {a_num} -> B: {b_num}",
                            "近 3 期成功發動次數": hit_count,
                            "狀態建議": status
                        })
                        
                    st.dataframe(pd.DataFrame(validation_results), use_container_width=True, hide_index=True)

                else:
                    st.warning("🧐 過去 3 期中，無連動率大於 15% 的組合。")

        st.markdown("---")
        
        st.markdown("### ⭐ 步驟四：1星至10星 下期號碼推薦")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            star_selection = st.selectbox("請選擇玩法：", [f"{i}星" for i in range(1, 11)])
            target_count = int(star_selection.replace("星", ""))
            
        with col2:
            st.write("") 
            st.write("")
            analyze_btn = st.button("🎲 產生推薦號碼")
            
        if analyze_btn:
            all_numbers = []
            for num_list in df_analysis["號碼清單"]:
                all_numbers.extend(num_list)
                
            counter = Counter(all_numbers)
            most_common = counter.most_common(target_count)
            result_nums = [item[0] for item in most_common]
            
            st.success(f"🎊 **{star_selection} 推薦下注號碼**： **{', '.join(result_nums)}**")
            
            st.write("📋 **詳細統計 (近 3 期出現次數)：**")
            for num, count in most_common:
                st.write(f"- 🟢 **{num}號**: 出現 {count} 次")

elif menu == "設定 (準備中)":
    st.write("保留擴充區塊。")