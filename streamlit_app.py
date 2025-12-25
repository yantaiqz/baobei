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
# 1. 全局配置 & CSS（优化文字对比度）
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
        color: #ffffff !important; /* 基础文字白色 */
    }
    MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* === 顶部 HUD 仪表盘 === */
    .hud-container {
        display: flex; justify-content: space-between; align-items: center;
        background: rgba(20, 20, 20, 0.8);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255,255,255,0.15);
        padding: 15px 30px; margin: -1rem -1rem 20px -1rem;
        position: sticky; top: 0; z-index: 999;
    }
    .hud-title { font-size: 1.5rem; font-weight: 800; color: #ffffff !important; letter-spacing: 1px; }
    .hud-sub { font-size: 0.8rem; color: #e2e8f0 !important; text-transform: uppercase; letter-spacing: 2px; font-weight: 500; }
    
    /* === 统计数字样式（增强对比度） === */
    .stat-box { text-align: center; padding: 0 10px; }
    .stat-val { font-size: 1.8rem; font-weight: 700; color: #4ade80 !important; font-family: 'Courier New', monospace; }
    .stat-death-val { font-size: 1.8rem; font-weight: 700; color: #f87171 !important; font-family: 'Courier New', monospace; }
    .stat-label { font-size: 0.8rem; color: #f1f5f9 !important; text-transform: uppercase; margin-top: -5px; font-weight: 600; letter-spacing: 1px; }

    /* === 实时日志样式（增强可读性） === */
    .log-container {
        height: 120px; overflow-y: hidden;
        mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
        -webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
        border-left: 2px solid #64748b;
        padding-left: 10px;
    }
    .log-item {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem; margin-bottom: 4px;
        color: #ffffff !important;
        text-shadow: 0 0 3px rgba(0,0,0,0.9);
    }
    .death-log-item {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem; margin-bottom: 4px;
        color: #fca5a5 !important;
        text-shadow: 0 0 3px rgba(0,0,0,0.9);
    }

    /* === 咖啡/支付卡片优化（高对比度） === */
    .pay-amount-display { font-size: 2rem; font-weight: 800; color: #f87171 !important; margin: 10px 0; }
    .pay-label { font-size: 0.9rem; color: #f1f5f9 !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .color-wechat { color: #4ade80 !important; }
    .color-alipay { color: #60a5fa !important; }
    .color-paypal { color: #38bdf8 !important; }
    
    /* === 右上角按钮（增强可见性） === */
    .nav-btn {
        background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);
        color: #ffffff !important; padding: 5px 12px; border-radius: 20px; cursor: pointer;
        font-size: 0.8rem; text-decoration: none; display: inline-block;
    }
    .nav-btn:hover { background: rgba(255,255,255,0.3); color: white !important; }
    
    /* === 表格与容器（全白文字） === */
    [data-testid="stDataFrame"] { 
        background: transparent !important; 
        --background-color: transparent !important;
        color: #ffffff !important;
    }
    [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        color: #ffffff !important;
    }
    .streamlit-expanderHeader {
        color: #ffffff !important;
        font-weight: 600;
    }
    [data-testid="stDeckGlJsonChart"] {
        transition: opacity 0.2s ease-in-out !important;
        opacity: 1 !important;
    }
    
    /* === 按钮文字增强 === */
    button {
        color: #ffffff !important;
    }
    
    /* === 输入框文字优化 === */
    [data-testid="stNumberInput"] input {
        color: #ffffff !important;
    }
    
    /* === Tabs 文字优化 === */
    [data-testid="stTabs"] [data-testid="stTab"] {
        color: #ffffff !important;
    }
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
        'title': '中国各地人口实时变化',
        'subtitle': '左侧新生 · 右侧离去',
        'born_count': '本场新生',
        'death_count': '本场离世',
        'log_boy': '{time} - {prov} 迎来了一位男孩',
        'log_girl': '{time} - {prov} 迎来了一位女孩',
        'log_death': '{time} - {prov} 有一位居民离世',
        'coffee_title': '请开发者喝咖啡',
        'coffee_desc': '如果这些工具帮到了你，欢迎支持老登的创作！',
        'coffee_btn': "☕ 请开发者喝咖啡",
        'coffee_close': "🔼 收起打赏",
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
        'coffee_close': "🔼 Close Donation",
        'pay_success': "Received! Thanks for the coffee! ❤️",
        'pay_wechat': 'WeChat', 'pay_alipay': 'Alipay', 'pay_paypal': 'PayPal',
        'more_app': 'More Apps', 'coffee_amount': "Enter Coffee Count",
        'stat_tab_title': "📊 Provincial Statistics"
    }
}

# ==========================================
# 3. 状态管理（包含打赏显示状态）
# ==========================================
def init_session():
    defaults = {
        'start_time': datetime.datetime.now(),
        'language': 'zh',
        'coffee_num': 1,
        'has_counted': False,
        'show_donate': False,  # 打赏模块显示状态（默认隐藏）
        'total_born': 0,
        'total_death': 0,
        'born_log': [],
        'death_log': [],
        'birth_map_data': pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name', 'born_time'], dtype=object),
        'death_map_data': pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name', 'death_time'], dtype=object),
        'prov_stats': {p['zh']: {'born': 0, 'death': 0, 'en': p['en']} for p in PROVINCES},
        'birth_view_state': pdk.ViewState(latitude=35.0, longitude=105.0, zoom=3.0, pitch=20),
        'death_view_state': pdk.ViewState(latitude=35.0, longitude=105.0, zoom=3.0, pitch=20),
        'donate_success': False  # 打赏成功提示状态
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v

init_session()
TXT = TEXTS[st.session_state.language]
def get_txt(key): return TEXTS[st.session_state.language].get(key, key)

# ==========================================
# 4. 核心逻辑函数
# ==========================================
DB_FILE = os.path.expanduser("~/baby_map.db")

def track_stats():
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
    except Exception as e:
        pass

track_stats()

def generate_baby():
    prov = random.choices(PROVINCES, weights=PROV_WEIGHTS, k=1)[0]
    gender = random.choice(['m', 'f'])
    color = [0, 255, 255, 200] if gender == 'm' else [255, 0, 255, 200]
    st.session_state.prov_stats[prov['zh']]['born'] += 1
    return {"zh": prov["zh"], "en": prov["en"], "gender": gender, "lat": prov['lat'], "lon": prov['lon'], "color": color}

def generate_death():
    prov = random.choices(PROVINCES, weights=PROV_WEIGHTS, k=1)[0]
    color = [248, 113, 113, 200] 
    st.session_state.prov_stats[prov['zh']]['death'] += 1
    return {"zh": prov["zh"], "en": prov["en"], "lat": prov['lat'], "lon": prov['lon'], "color": color}

# ==========================================
# 5. 地图渲染
# ==========================================
def create_map_layers(data, layer_type="birth"):
    if data.empty: return []
    common_layer_props = {
        "filled": True, 
        "opacity": 0.8, 
        "radius_min_pixels": 10, 
        "radius_max_pixels": 120, 
        "get_line_color": [255, 255, 255, 100], 
        "get_line_width": 2000
    }
    scatter_layer = pdk.Layer(
        "ScatterplotLayer", 
        data=data, 
        get_position='[lon, lat]', 
        get_fill_color='color', 
        get_radius='size', 
        **common_layer_props
    )
    text_layer = pdk.Layer(
        "TextLayer", 
        data=data, 
        get_position='[lon, lat]', 
        get_text='name', 
        get_color=[255, 255, 255], 
        get_size=20, 
        get_alignment_baseline="'bottom'", 
        get_text_anchor="'middle'"
    )
    return [scatter_layer, text_layer]

def render_map(placeholder, data, view_state, title, layer_type):
    layers = create_map_layers(data, layer_type)
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json", 
        initial_view_state=view_state, 
        layers=layers, 
        tooltip=False, 
        map_provider=None, 
        api_keys={}
    )
    placeholder.markdown(f"<h4 style='text-align:center; color:#4ade80;'>{title}</h4>", unsafe_allow_html=True)
    placeholder.pydeck_chart(deck, use_container_width=True)

# ==========================================
# 6. UI: 顶部 HUD
# ==========================================
c_hud_1, c_hud_2 = st.columns([0.6, 0.4])
with c_hud_1:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px;">
        <div style="font-size:2.5rem;">👶</div>
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
        st.markdown(
            f'<a href="https://laodeng.streamlit.app" target="_blank" class="nav-btn" style="text-align:center; width:100%; padding: 8px 0;">{TXT["more_app"]} ↗</a>', 
            unsafe_allow_html=True
        )

# ==========================================
# 7. 双地图布局
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
# 9. 动画主循环
# ==========================================
REFRESH_RATE = 0.8
BIRTH_PROB = 0.6
DEATH_PROB = 0.5
CLEAN_INTERVAL = 5
clean_counter = 0

while True:
    ts = time.time()
    t_str = datetime.datetime.now().strftime('%H:%M:%S')
    clean_counter += 1
    
    # 生成出生数据
    if random.random() < BIRTH_PROB:
        st.session_state.total_born += 1
        baby = generate_baby()
        p_name = baby['zh'] if st.session_state.language == 'zh' else baby['en']
        log_key = 'log_boy' if baby['gender'] == 'm' else 'log_girl'
        log_text = get_txt(log_key).format(time=t_str, prov=p_name)
        st.session_state.born_log.insert(0, {"t": log_text, "c": baby['color']})
        if len(st.session_state.born_log) > 6: 
            st.session_state.born_log.pop()
        new_row = pd.DataFrame([{
            'lat': baby['lat'], 
            'lon': baby['lon'], 
            'color': baby['color'], 
            'size': 80000, 
            'born_time': ts, 
            'name': p_name
        }])
        st.session_state.birth_map_data = pd.concat(
            [st.session_state.birth_map_data, new_row], 
            ignore_index=True
        )

    # 生成死亡数据
    if random.random() < DEATH_PROB:
        st.session_state.total_death += 1
        death = generate_death()
        p_name = death['zh'] if st.session_state.language == 'zh' else death['en']
        log_text = get_txt('log_death').format(time=t_str, prov=p_name)
        st.session_state.death_log.insert(0, {"t": log_text, "c": death['color']})
        if len(st.session_state.death_log) > 6: 
            st.session_state.death_log.pop()
        new_row = pd.DataFrame([{
            'lat': death['lat'], 
            'lon': death['lon'], 
            'color': death['color'], 
            'size': 30000, 
            'death_time': ts, 
            'name': p_name
        }])
        st.session_state.death_map_data = pd.concat(
            [st.session_state.death_map_data, new_row], 
            ignore_index=True
        )

    # 清理过期数据
    if clean_counter >= CLEAN_INTERVAL:
        for data_key, time_col in [('birth_map_data', 'born_time'), ('death_map_data', 'death_time')]:
            data = st.session_state[data_key]
            if not data.empty: 
                st.session_state[data_key] = data[data[time_col] > (ts - 3.0)]
        clean_counter = 0

    # 渲染统计区域
    with stats_placeholder.container():
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        with c1: 
            st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-val">{st.session_state.total_born}</div>
                    <div class="stat-label">{get_txt("born_count")}</div>
                </div>
            ''', unsafe_allow_html=True)
        with c2: 
            log_html = "".join([
                f'<div class="log-item" style="color:{"#22d3ee" if l["c"][0]==0 else "#e879f9"}">{l["t"]}</div>' 
                for l in st.session_state.born_log
            ])
            st.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
        with c3:
            death_log_html = "".join([
                f'<div class="death-log-item">{l["t"]}</div>' 
                for l in st.session_state.death_log
            ])
            st.markdown(f'<div class="log-container">{death_log_html}</div>', unsafe_allow_html=True)
        with c4: 
            st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-death-val">{st.session_state.total_death}</div>
                    <div class="stat-label">{get_txt("death_count")}</div>
                </div>
            ''', unsafe_allow_html=True)

    # 渲染地图
    render_map(
        birth_map_placeholder, 
        st.session_state.birth_map_data, 
        st.session_state.birth_view_state, 
        get_txt('born_count'), 
        "birth"
    )
    render_map(
        death_map_placeholder, 
        st.session_state.death_map_data, 
        st.session_state.death_view_state, 
        get_txt('death_count'), 
        "death"
    )
        
    # 渲染省份数据表格
    with prov_table_placeholder.container():
        with st.expander(get_txt('stat_tab_title'), expanded=True):
            prov_data = []
            for prov_zh, stats in st.session_state.prov_stats.items():
                prov_data.append({
                    '省份': prov_zh, 
                    'Province': stats['en'], 
                    '新生': stats['born'], 
                    'Born': stats['born'], 
                    '离世': stats['death'], 
                    'Deaths': stats['death']
                })
            df_stats = pd.DataFrame(prov_data)
            df_stats['Total'] = df_stats['新生'] + df_stats['离世']
            df_stats = df_stats.sort_values(by='Total', ascending=False).head(10)
            
            if st.session_state.language == 'zh':
                display_cols = ['省份', '新生', '离世']
                cols_cfg = {
                    "新生": st.column_config.ProgressColumn(
                        "新生", format="%d", 
                        min_value=0, max_value=max(int(df_stats['新生'].max()), 10)
                    ),
                    "离世": st.column_config.ProgressColumn(
                        "离世", format="%d",
                        min_value=0, max_value=max(int(df_stats['离世'].max()), 10)
                    )
                }
            else:
                display_cols = ['Province', 'Born', 'Deaths']
                cols_cfg = {
                    "Born": st.column_config.ProgressColumn(
                        "Born", format="%d",
                        min_value=0, max_value=max(int(df_stats['Born'].max()), 10)
                    ),
                    "Deaths": st.column_config.ProgressColumn(
                        "Deaths", format="%d",
                        min_value=0, max_value=max(int(df_stats['Deaths'].max()), 10)
                    )
                }
            st.dataframe(
                df_stats[display_cols],
                use_container_width=True,
                column_config=cols_cfg,
                hide_index=True
            )

    time.sleep(REFRESH_RATE)
