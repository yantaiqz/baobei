import streamlit as st
import pydeck as pdk
import pandas as pd
import sqlite3
import uuid
import datetime
import os
import time
import random

# ==========================================
# 1. 全局配置 & CSS
# ==========================================
st.set_page_config(
    page_title="China Life & Death | 生死观测台",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* === 全局暗黑沉浸式背景 === */
    .stApp {
        background-color: #0e1117 !important;
        color: #e0e0e0;
    }
    MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* === 顶部 HUD 仪表盘 === */
    .hud-container {
        display: flex; justify-content: space-between; align-items: center;
        background: rgba(20, 20, 20, 0.6);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding: 15px 30px; margin: -1rem -1rem 20px -1rem;
        position: sticky; top: 0; z-index: 999;
    }
    .hud-title { font-size: 1.5rem; font-weight: 800; color: #fff; letter-spacing: 1px; }
    .hud-sub { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 2px; }
    
    /* === 统计数字样式 === */
    .stat-box { text-align: center; padding: 0 10px; }
    .stat-val { font-size: 1.8rem; font-weight: 700; color: #4ade80; font-family: 'Courier New', monospace; }
    .stat-death-val { font-size: 1.8rem; font-weight: 700; color: #f87171; font-family: 'Courier New', monospace; }
    .stat-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; margin-top: -5px; }

    /* === 实时日志样式 === */
    .log-container {
        height: 120px; overflow-y: hidden;
        mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
        -webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
        border-left: 2px solid #333;
        padding-left: 10px;
    }
    .log-item {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem; margin-bottom: 4px;
        text-shadow: 0 0 5px rgba(0,0,0,0.5);
    }
    .death-log-item {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem; margin-bottom: 4px;
        color: #f87171;
        text-shadow: 0 0 5px rgba(0,0,0,0.5);
    }

    /* === 咖啡/支付卡片 === */
    .pay-amount-display { font-size: 2rem; font-weight: 800; color: #f87171; margin: 10px 0; }
    .pay-label { font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
    
    /* === 右上角按钮 === */
    .nav-btn {
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.1);
        color: #ddd; padding: 5px 12px; border-radius: 20px; cursor: pointer;
        font-size: 0.8rem; text-decoration: none; display: inline-block;
    }
    .nav-btn:hover { background: rgba(255,255,255,0.2); color: white; }
    
    /* === 表格样式修正 === */
    [data-testid="stDataFrame"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心数据
# ==========================================
PROVINCES = [
    {"zh": "广东", "en": "Guangdong", "lat": 23.1, "lon": 113.2, "weight": 126},
    {"zh": "山东", "en": "Shandong", "lat": 36.6, "lon": 117.0, "weight": 101},
    {"zh": "河南", "en": "Henan", "lat": 34.7, "lon": 113.6, "weight": 98},
    {"zh": "四川", "en": "Sichuan", "lat": 30.6, "lon": 104.0, "weight": 83},
    {"zh": "江苏", "en": "Jiangsu", "lat": 32.0, "lon": 118.7, "weight": 85},
    {"zh": "河北", "en": "Hebei", "lat": 38.0, "lon": 114.5, "weight": 74},
    {"zh": "湖南", "en": "Hunan", "lat": 28.2, "lon": 112.9, "weight": 66},
    {"zh": "浙江", "en": "Zhejiang", "lat": 30.2, "lon": 120.1, "weight": 65},
    {"zh": "安徽", "en": "Anhui", "lat": 31.8, "lon": 117.2, "weight": 61},
    {"zh": "湖北", "en": "Hubei", "lat": 30.5, "lon": 114.3, "weight": 58},
    {"zh": "广西", "en": "Guangxi", "lat": 22.8, "lon": 108.3, "weight": 50},
    {"zh": "云南", "en": "Yunnan", "lat": 25.0, "lon": 102.7, "weight": 47},
    {"zh": "江西", "en": "Jiangxi", "lat": 28.6, "lon": 115.9, "weight": 45},
    {"zh": "辽宁", "en": "Liaoning", "lat": 41.8, "lon": 123.4, "weight": 42},
    {"zh": "福建", "en": "Fujian", "lat": 26.0, "lon": 119.2, "weight": 41},
    {"zh": "陕西", "en": "Shaanxi", "lat": 34.2, "lon": 108.9, "weight": 39},
    {"zh": "黑龙江", "en": "Heilongjiang", "lat": 45.7, "lon": 126.6, "weight": 31},
    {"zh": "山西", "en": "Shanxi", "lat": 37.8, "lon": 112.5, "weight": 34},
    {"zh": "贵州", "en": "Guizhou", "lat": 26.6, "lon": 106.6, "weight": 38},
    {"zh": "重庆", "en": "Chongqing", "lat": 29.5, "lon": 106.5, "weight": 32},
    {"zh": "吉林", "en": "Jilin", "lat": 43.8, "lon": 125.3, "weight": 23},
    {"zh": "甘肃", "en": "Gansu", "lat": 36.0, "lon": 103.8, "weight": 24},
    {"zh": "内蒙古", "en": "Inner Mongolia", "lat": 40.8, "lon": 111.7, "weight": 24},
    {"zh": "新疆", "en": "Xinjiang", "lat": 43.8, "lon": 87.6, "weight": 25},
    {"zh": "上海", "en": "Shanghai", "lat": 31.2, "lon": 121.4, "weight": 24},
    {"zh": "北京", "en": "Beijing", "lat": 39.9, "lon": 116.4, "weight": 21},
    {"zh": "天津", "en": "Tianjin", "lat": 39.0, "lon": 117.2, "weight": 13},
    {"zh": "海南", "en": "Hainan", "lat": 20.0, "lon": 110.3, "weight": 10},
    {"zh": "宁夏", "en": "Ningxia", "lat": 38.4, "lon": 106.2, "weight": 7},
    {"zh": "青海", "en": "Qinghai", "lat": 36.6, "lon": 101.7, "weight": 5},
    {"zh": "西藏", "en": "Tibet", "lat": 29.6, "lon": 91.1, "weight": 3},
]
PROV_WEIGHTS = [p['weight'] for p in PROVINCES]

TEXTS = {
    'zh': {
        'title': '中国人口实时模拟',
        'subtitle': '左侧新生 · 右侧离去',
        'born_count': '本场新生',
        'death_count': '本场离世',
        'log_boy': '{time} - {prov} 迎来了一位男孩',
        'log_girl': '{time} - {prov} 迎来了一位女孩',
        'log_death': '{time} - {prov} 有一位居民离世',
        'coffee_title': '请开发者喝咖啡',
        'coffee_desc': '如果这些工具帮到了你，欢迎支持老登的创作！',
        'coffee_btn': "☕ 请开发者喝咖啡",
        'pay_success': "收到！感谢打赏。代码写得更有劲了！❤️",
        'pay_wechat': '微信支付', 'pay_alipay': '支付宝', 'pay_paypal': '贝宝',
        'more_app': '更多应用', 'coffee_amount': "请输入打赏杯数",
        'stat_tab_title': "📊 各省数据监控看板"
    },
    'en': {
        'title': 'China Population Sim',
        'subtitle': 'Births (Left) vs Deaths (Right)',
        'born_count': 'Session Births',
        'death_count': 'Session Deaths',
        'log_boy': '{time} - {prov} welcomed a baby boy',
        'log_girl': '{time} - {prov} welcomed a baby girl',
        'log_death': '{time} - {prov} lost a resident',
        'coffee_title': 'Buy me a coffee',
        'coffee_desc': 'Help keep the server running!',
        'coffee_btn': "☕ Buy me a coffee",
        'pay_success': "Received! Thanks for the coffee! ❤️",
        'pay_wechat': 'WeChat', 'pay_alipay': 'Alipay', 'pay_paypal': 'PayPal',
        'more_app': 'More Apps', 'coffee_amount': "Enter Coffee Count",
        'stat_tab_title': "📊 Provincial Statistics"
    }
}

# ==========================================
# 3. 状态管理
# ==========================================
def init_session():
    defaults = {
        'start_time': datetime.datetime.now(),
        'language': 'zh',
        'coffee_num': 1,
        'has_counted': False,
        'total_born': 0,
        'total_death': 0,
        'born_log': [],
        'death_log': [],
        'birth_map_data': pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name', 'born_time']),
        'death_map_data': pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name', 'death_time']),
        'prov_stats': {p['zh']: {'born': 0, 'death': 0} for p in PROVINCES}
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()
TXT = TEXTS[st.session_state.language]
def get_txt(key): return TEXTS[st.session_state.language][key]

# ==========================================
# 4. 核心逻辑函数
# ==========================================
DB_FILE = os.path.expanduser("~/baby_map.db")

def track_stats():
    """轻量级 SQLite 统计"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stats (date TEXT, type TEXT, val INTEGER, UNIQUE(date, type))''')
        today = datetime.datetime.utcnow().date().isoformat()
        if not st.session_state.has_counted:
            c.execute("INSERT OR IGNORE INTO stats VALUES (?, 'pv', 0)", (today,))
            c.execute("UPDATE stats SET val = val + 1 WHERE date=? AND type='pv'", (today,))
            conn.commit()
            st.session_state.has_counted = True
        conn.close()
    except: pass

track_stats()

def generate_baby():
    prov = random.choices(PROVINCES, weights=PROV_WEIGHTS, k=1)[0]
    gender = random.choice(['m', 'f'])
    color = [0, 255, 255, 200] if gender == 'm' else [255, 0, 255, 200]
    st.session_state.prov_stats[prov['zh']]['born'] += 1
    return {"zh": prov["zh"], "en": prov["en"], "gender": gender, "lat": prov['lat'], "lon": prov['lon'], "color": color}

def generate_death():
    prov = random.choices(PROVINCES, weights=PROV_WEIGHTS, k=1)[0]
    color = [248, 113, 113, 200] # Red
    st.session_state.prov_stats[prov['zh']]['death'] += 1
    return {"zh": prov["zh"], "en": prov["en"], "lat": prov['lat'], "lon": prov['lon'], "color": color}

# ==========================================
# 5. UI: 顶部 HUD
# ==========================================
c_hud_1, c_hud_2 = st.columns([0.6, 0.4])
with c_hud_1:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px;">
        <div style="font-size:2.5rem;">☯️</div>
        <div>
            <div class="hud-title">{TXT['title']}</div>
            <div class="hud-sub">{TXT['subtitle']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_hud_2:
    cols = st.columns([1, 1, 1])
    with cols[1]:
        lang_btn = "🌐 EN" if st.session_state.language == 'zh' else "🌐 中"
        if st.button(lang_btn, use_container_width=True):
            st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
            st.rerun()
    with cols[2]:
        st.markdown(f'<a href="https://laodeng.streamlit.app" target="_blank" class="nav-btn" style="text-align:center; width:100%; padding: 8px 0;">{TXT["more_app"]} ↗</a>', unsafe_allow_html=True)

# ==========================================
# 6. 双地图布局
# ==========================================
st.write("")
col_birth, col_death = st.columns(2, gap="medium")
birth_map_placeholder = col_birth.empty()
death_map_placeholder = col_death.empty()

# 统计区域
stats_placeholder = st.empty()

# 省份数据表格
st.markdown("---")
prov_table_placeholder = st.empty()


# ==========================================
# 7. 咖啡打赏 (核心修复区域)
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    @st.dialog(" " + get_txt('coffee_title'), width="small")
    def show_coffee_window():
        st.markdown(f"""<div style="text-align:center; color:#666; margin-bottom:15px;">{get_txt('coffee_desc')}</div>""", unsafe_allow_html=True)
        
        # --- 修复 1：快捷按钮 ---
        # 逻辑：点击后直接修改 Session State 并 Rerun，强制刷新下方 Input 框的值
        presets = [("☕", 1), ("🍗", 3), ("🚀", 5)]
        cols = st.columns(3, gap="small")
        for i, (icon, num) in enumerate(presets):
            with cols[i]:
                if st.button(f"{icon} {num}", use_container_width=True, key=f"p_btn_{i}"): 
                    st.session_state.coffee_num = num
                    st.rerun()

        st.write("")
        # Input 绑定 Session State，确保双向同步
        cnt = st.number_input(get_txt('coffee_amount'), 1, 100, step=1, key='coffee_num')
        
        cny_total = cnt * 10
        usd_total = cnt * 2

        def render_pay_tab(title, amount_str, color_class, img_path, qr_data_suffix, link_url=None):
            with st.container(border=True):
                st.markdown(f"""<div style="text-align: center;"><div class="pay-amount-display {color_class}">{amount_str}</div></div>""", unsafe_allow_html=True)
                c_img_1, c_img_2, c_img_3 = st.columns([1, 4, 1])
                with c_img_2:
                    if os.path.exists(img_path): st.image(img_path, use_container_width=True)
                    else: 
                        qr_data = f"Donate_{cny_total}_{qr_data_suffix}"
                        if link_url: qr_data = link_url
                        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={qr_data}", use_container_width=True)
                if link_url:
                    st.write("")
                    st.link_button(f"👉 Pay {amount_str}", link_url, type="primary", use_container_width=True)
                else:
                    st.markdown(f"""<div style="text-align: center; font-size: 0.8rem; color:#888;">扫描二维码支持</div>""", unsafe_allow_html=True)
                    
        st.write("")
        t1, t2, t3 = st.tabs([get_txt('pay_wechat'), get_txt('pay_alipay'), get_txt('pay_paypal')])
        with t1: render_pay_tab("WeChat Pay", f"¥{cny_total}", "color-wechat", "wechat_pay.jpg", "WeChat")
        with t2: render_pay_tab("Alipay", f"¥{cny_total}", "color-alipay", "ali_pay.jpg", "Alipay")
        with t3: render_pay_tab("PayPal", f"${usd_total}", "color-paypal", "paypal.png", "PayPal", "https://paypal.me/ytqz")
        
        st.write("")
        
        # --- 修复 2：打赏动画按钮 ---
        # 逻辑：点击 -> 吐司提示 -> 气球动画 -> 睡眠展示 -> 关闭弹窗(Rerun)
        if st.button("🎉 " + get_txt('pay_success').split('!')[0], type="primary", use_container_width=True):
            # 1. 顶部弹出 Toast，提示会持久化一点
            st.toast(get_txt('pay_success').format(count=cnt), icon="❤️")
            # 2. 页面飘气球
            st.balloons()
            # 3. 等待足够时间让用户看到动画 (在 dialog 关闭前)
            time.sleep(2.0)
            # 4. 刷新页面（同时也关闭了 dialog）
            st.rerun()

    if st.button(get_txt('coffee_btn'), use_container_width=True):
        show_coffee_window()

# ==========================================
# 8. 动画主循环
# ==========================================
birth_view_state = pdk.ViewState(latitude=35.0, longitude=105.0, zoom=3.0, pitch=20)
death_view_state = pdk.ViewState(latitude=35.0, longitude=105.0, zoom=3.0, pitch=20)
REFRESH_RATE = 0.8
BIRTH_PROB = 0.6
DEATH_PROB = 0.5

while True:
    ts = time.time()
    t_str = datetime.datetime.now().strftime('%H:%M:%S')
    
    # 1. 生成出生数据
    if random.random() < BIRTH_PROB:
        st.session_state.total_born += 1
        baby = generate_baby()
        p_name = baby['zh'] if st.session_state.language == 'zh' else baby['en']
        
        key = 'log_boy' if baby['gender']=='m' else 'log_girl'
        st.session_state.born_log.insert(0, {"t": TXT[key].format(time=t_str, prov=p_name), "c": baby['color']})
        if len(st.session_state.born_log) > 6: st.session_state.born_log.pop()
        
        new_row = pd.DataFrame([{'lat': baby['lat'], 'lon': baby['lon'], 'color': baby['color'], 'size': 30000, 'born_time': ts, 'name': p_name}])
        if st.session_state.birth_map_data.empty: st.session_state.birth_map_data = new_row
        else: st.session_state.birth_map_data = pd.concat([st.session_state.birth_map_data, new_row], ignore_index=True)

    # 2. 生成死亡数据
    if random.random() < DEATH_PROB:
        st.session_state.total_death += 1
        death = generate_death()
        p_name = death['zh'] if st.session_state.language == 'zh' else death['en']
        
        st.session_state.death_log.insert(0, {"t": TXT['log_death'].format(time=t_str, prov=p_name), "c": death['color']})
        if len(st.session_state.death_log) > 6: st.session_state.death_log.pop()
        
        new_row = pd.DataFrame([{'lat': death['lat'], 'lon': death['lon'], 'color': death['color'], 'size': 30000, 'death_time': ts, 'name': p_name}])
        if st.session_state.death_map_data.empty: st.session_state.death_map_data = new_row
        else: st.session_state.death_map_data = pd.concat([st.session_state.death_map_data, new_row], ignore_index=True)

    # 3. 清理过期点
    for k, time_col in [('birth_map_data', 'born_time'), ('death_map_data', 'death_time')]:
        if not st.session_state[k].empty:
            st.session_state[k] = st.session_state[k][st.session_state[k][time_col] > (ts - 2.5)]

    # 4. 渲染统计区
    with stats_placeholder.container():
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        with c1: st.markdown(f'<div class="stat-box"><div class="stat-val">{st.session_state.total_born}</div><div class="stat-label">{TXT["born_count"]}</div></div>', unsafe_allow_html=True)
        with c2: 
            h = "".join([f'<div class="log-item" style="color:{"#22d3ee" if l["c"][0]==0 else "#e879f9"}">{l["t"]}</div>' for l in st.session_state.born_log])
            st.markdown(f'<div class="log-container">{h}</div>', unsafe_allow_html=True)
        with c3:
            h = "".join([f'<div class="death-log-item">{l["t"]}</div>' for l in st.session_state.death_log])
            st.markdown(f'<div class="log-container">{h}</div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="stat-box"><div class="stat-death-val">{st.session_state.total_death}</div><div class="stat-label">{TXT["death_count"]}</div></div>', unsafe_allow_html=True)

    # 5. 渲染地图
    def get_deck(data, t_col, color_hex):
        return pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            initial_view_state=birth_view_state,
            layers=[
                pdk.Layer("ScatterplotLayer", data, get_position='[lon, lat]', get_fill_color='color', get_radius='size', filled=True, radius_min_pixels=5, radius_max_pixels=60),
                pdk.Layer("TextLayer", data, get_position='[lon, lat]', get_text='name', get_color=[255,255,255], get_size=15, get_alignment_baseline="'bottom'")
            ]
        )
    
    with birth_map_placeholder:
        st.markdown(f"<h4 style='text-align:center; color:#4ade80'>{TXT['born_count']}</h4>", unsafe_allow_html=True)
        st.pydeck_chart(get_deck(st.session_state.birth_map_data, 'born_time', '#4ade80'), use_container_width=True)
    
    with death_map_placeholder:
        st.markdown(f"<h4 style='text-align:center; color:#f87171'>{TXT['death_count']}</h4>", unsafe_allow_html=True)
        st.pydeck_chart(get_deck(st.session_state.death_map_data, 'death_time', '#f87171'), use_container_width=True)
        
    # 6. 渲染各省数据监控看板
    with prov_table_placeholder.container():
        with st.expander(TXT['stat_tab_title'], expanded=True):
            df_stats = pd.DataFrame.from_dict(st.session_state.prov_stats, orient='index')
            df_stats = df_stats.reset_index().rename(columns={'index': '省份', 'born': '新生', 'death': '离世'})
            if st.session_state.language == 'en':
                df_stats = df_stats.rename(columns={'省份': 'Province', '新生': 'Born', '离世': 'Deaths'})
            
            df_stats['Total'] = df_stats.iloc[:, 1] + df_stats.iloc[:, 2]
            df_stats = df_stats.sort_values(by='Total', ascending=False).head(10)
            
            st.dataframe(
                df_stats[['省份', '新生', '离世'] if st.session_state.language == 'zh' else ['Province', 'Born', 'Deaths']],
                use_container_width=True,
                column_config={
                    "新生": st.column_config.ProgressColumn("新生 (Born)", format="%d", min_value=0, max_value=max(df_stats.iloc[:, 1].max(), 10)),
                    "离世": st.column_config.ProgressColumn("离世 (Deaths)", format="%d", min_value=0, max_value=max(df_stats.iloc[:, 2].max(), 10)),
                },
                hide_index=True
            )

    time.sleep(REFRESH_RATE)
