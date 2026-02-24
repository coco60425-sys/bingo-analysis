import streamlit as st
import pandas as pd
import re
from collections import Counter
from itertools import combinations
from bs4 import BeautifulSoup
import cloudscraper

# --- UI 視覺樣式設定 ---
st.set_page_config(page_title="BINGO 分析系統", layout="wide")
st.markdown("""
<style>
    .card { background-color: #F8F9F9; padding: 20px; border-radius: 8px; border-left: 5px solid #2E86C1; margin-bottom: 15px; }
    .stButton>button { width: 100%; background-color: #2E86C1; color: white; border-radius: 5px; }
    .tag { background: #EDF2F7; color: #2D3748; padding: 4px 10px; border-radius: 4px; margin: 2px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

st.title("BINGO 數據分析系統 (輕量自動版)")

if st.button("🔄 自動獲取最新數據並分析"):
    with st.spinner("連線獲取數據中..."):
        try:
            # 1. 輕量級抓取 (避開基礎防爬蟲機制，無須 Selenium)
            scraper = cloudscraper.create_scraper()
            url = "https://lotto.auzonet.com/bingobingo.php"
            response = scraper.get(url, timeout=10)
            response.raise_for_status()
            
            # 2. 解析 HTML 結構
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr")
            parsed_data = []
            seen_issues = set()
            
            for row in rows:
                row_text = row.get_text(separator=" ", strip=True)
                issue_match = re.search(r'(11\d{7})', row_text)
                if not issue_match: continue
                issue_str = issue_match.group(1)
                if issue_str in seen_issues: continue
                
                clean_text = re.sub(r'\d{2}:\d{2}(:\d{2})?', ' ', row_text)
                raw_nums = re.findall(r'\b\d{1,2}\b', clean_text)
                valid_nums = [f"{int(n):02d}" for n in raw_nums if 1 <= int(n) <= 80]
                
                draw_nums = []
                for n in valid_nums:
                    if n not in draw_nums and len(draw_nums) < 20: draw_nums.append(n)
                        
                if len(draw_nums) == 20:
                    parsed_data.append({"issue": issue_str, "nums": draw_nums})
                    seen_issues.add(issue_str)
                if len(parsed_data) == 4: break

            if len(parsed_data) < 4:
                st.error("🛑 數據抓取不足 4 期。")
                st.stop()

            # 3. 數據分析 (排除第一期，分析後 3 期)
            df_analysis = parsed_data[1:4]
            analyzed_issues = [d['issue'] for d in df_analysis]
            
            all_nums = []
            for d in df_analysis: all_nums.extend(d['nums'])
            counts = Counter(all_nums)
            
            pair_counts = Counter()
            for d in df_analysis:
                pairs = combinations(sorted(d['nums']), 2)
                pair_counts.update(pairs)
            top_pairs = pair_counts.most_common(5)

            # 4. 顯示客觀結果
            st.success(f"✅ 抓取成功。分析基準期數：{', '.join(analyzed_issues)}")
            
            st.markdown("<div class='card'><h4>📊 機率判讀與熱門推薦</h4></div>", unsafe_allow_html=True)
            for star in [1, 2, 3, 4, 5, 10]:
                top_n = [item[0] for item in counts.most_common(star)]
                tags = "".join([f"<span class='tag'>{n}</span>" for n in top_n])
                st.markdown(f"**{star} 星推薦**：{tags}", unsafe_allow_html=True)
            
            st.markdown("<div class='card'><h4>🔗 AB 連動率分析 (高頻雙星)</h4></div>", unsafe_allow_html=True)
            for pair, count in top_pairs:
                if count > 1:
                    st.markdown(f"<span class='tag'>{pair[0]}</span> & <span class='tag'>{pair[1]}</span> (共現次數: {count})", unsafe_allow_html=True)
            if top_pairs[0][1] <= 1:
                st.info("當前 3 期樣本中，無顯著的高頻連動組合。")

        except Exception as e:
            st.error(f"🛑 系統連線錯誤：{e}")
