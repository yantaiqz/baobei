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
# 1. 全局配置
# ==========================================
st.set_page_config(
    page_title="中国宝宝地图 | AI Data",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. 状态初始化 (合并)
# ==========================================
# --- 模板状态 ---
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
    st.session_state.access_status = 'free'
    st.session_state.unlock_time = None
if 'language' not in st.session_state:
    st.session_state.language = 'zh'
if 'coffee_num' not in st.session_state:
    st.session_state.coffee_num = 1
if 'visitor_id' not in st.session_state:
    st.session_state["visitor_id"] = str(uuid.uuid4())
if 'has_counted' not in st.session_state:
    st.session_state.has_counted = False

# --- 地图状态 ---
if 'total_born' not in st.session_state:
    st.session_state.total_born = 0
if 'born_log' not in st.session_state:
    st.session_state.born_log = [] 
if 'map_data' not in st.session_state:
    st.session_state.map_data = pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name'])

# ==========================================
# 3. 样式合并 (暗黑模式适配)
# ==========================================
st.markdown("""
<style>
    /* === 全局暗黑背景 === */
    .stApp {
        background-color: #0e1117 !important;
        color: #fff;
    }
    #MainMenu, footer, header {visibility: hidden;}

    /* === 右上角按钮 (暗黑版) === */
    .neal-btn {
        font-family: 'Inter', sans-serif; 
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        color: #eee; font-weight: 600;
        padding: 8px 16px; border-radius: 8px; cursor: pointer;
        transition: all 0.2s; display: inline-flex; align-items: center;
        justify-content: center; text-decoration: none !important;
        width: 100%;
    }
    .neal-btn:hover { background: rgba(255,255,255,0.2); border-color: #fff; transform: translateY(-1px); }
    .neal-btn-link { text-decoration: none; width: 100%; display: block; }

    /* === 统计条 (暗黑版) === */
    .stats-bar {
        display: flex; justify-content: center; gap: 25px; margin-top: 20px; 
        padding: 15px 25px; 
        background: rgba(255, 255, 255, 0.05); /* 半透明背景 */
        border-radius: 50px; 
        border: 1px solid rgba(255,255,255,0.1); 
        color: #aaa; font-size: 0.85rem; 
        width: fit-content; margin-left: auto; margin-right: auto; 
    }
    .stats-num { font-weight:700; color:#fff; }

    /* === 咖啡卡片 (暗黑版) === */
    .coffee-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151; border-radius: 16px;
        padding: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        margin-bottom: 10px; text-align: center; color: white;
    }
    .price-tag-container {
        background: rgba(220, 38, 38, 0.1); border: 1px dashed #ef4444;
        border-radius: 12px; padding: 10px; text-align: center;
        margin-top: 5px;
    }
    .price-label { color: #9ca3af; font-size: 0.8rem; }
    .price-number { color: #f87171; font-weight: 900; font-size: 1.8rem; }
    
    /* === 支付卡片 === */
    .pay-card {
        background: #1f2937; border: 1px solid #374151;
        border-radius: 12px; padding: 20px; text-align: center;
        margin-top: 10px; color: white;
    }
    .pay-amount-display { font-family: monospace; font-size: 1.8rem; font-weight: 800; margin: 10px 0; color: white; }
    .pay-instruction { font-size: 0.8rem; color: #9ca3af; margin-top: 15px; }
    
    /* === 地图统计卡片 === */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px; padding: 15px;
        text-align: center; color: white; margin-bottom: 10px;
    }
    .big-number {
        font-size: 2.5rem; font-weight: 800;
        background: -webkit-linear-gradient(#eee, #999);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    /* 语言切换位置 */
    [data-testid="button-lang_switch"] {
        position: fixed; top: 20px; right: 120px; z-index: 9999;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 常量与配置
# ==========================================
FREE_PERIOD_SECONDS = 600  # 试用增加到600秒方便演示
ACCESS_DURATION_HOURS = 24
UNLOCK_CODE = "vip888"
DB_FILE = os.path.join(os.path.expanduser("~/"), "baby_map_stats.db")

# 城市数据
CITIES = [
    {"name": "北京", "lat": 39.9042, "lon": 116.4074, "weight": 21},
    {"name": "上海", "lat": 31.2304, "lon": 121.4737, "weight": 24},
    {"name": "广州", "lat": 23.1291, "lon": 113.2644, "weight": 18},
    {"name": "深圳", "lat": 22.5431, "lon": 114.0579, "weight": 17},
    {"name": "成都", "lat": 30.5728, "lon": 104.0668, "weight": 20},
    {"name": "重庆", "lat": 29.5630, "lon": 106.5516, "weight": 30},
    {"name": "武汉", "lat": 30.5928, "lon": 114.3055, "weight": 13},
    {"name": "西安", "lat": 34.3416, "lon": 108.9398, "weight": 12},
    {"name": "杭州", "lat": 30.2741, "lon": 120.1551, "weight": 12},
    {"name": "南京", "lat": 32.0603, "lon": 118.7969, "weight": 9},
    {"name": "郑州", "lat": 34.7466, "lon": 113.6253, "weight": 12},
    {"name": "长沙", "lat": 28.2282, "lon": 112.9388, "weight": 10},
    {"name": "沈阳", "lat": 41.8057, "lon": 123.4315, "weight": 9},
    {"name": "青岛", "lat": 36.0671, "lon": 120.3826, "weight": 10},
    {"name": "天津", "lat": 39.0842, "lon": 117.2009, "weight": 13},
]
CITY_CHOICES = [c for c in CITIES]
CITY_WEIGHTS = [c['weight'] for c in CITIES]

# 多语言文本
lang_texts = {
    'zh': {
        'coffee_title': '请老登喝杯咖啡 ☕',
        'coffee_desc': '服务器还在燃烧，电费还没着落...',
        'custom_count': '自定义数量 (杯)',
        'total_label': '总计投入',
        'pay_wechat': '微信支付',
        'pay_alipay': '支付宝',
        'pay_paypal': 'PayPal',
        'paid_btn': '🎉 我已支付，给老登打气！',
        'paid_toast': '收到！感谢你的 {count} 杯咖啡！地图加载更快了！❤️',
        'coffee_btn': '☕ 支持服务器电费',
        'coffee_amount': '请输入打赏杯数',
        'visitor_today': '今日 UV',
        'visitor_total': '历史 UV',
        'lock_msg': '🔒 免费试用结束',
        'lock_desc': '为了防止服务器被挤爆，请解锁完整访问权限。',
        'unlock_btn': '验证并解锁',
        'more_apps': '✨ 更多好玩应用'
    },
    'en': {
        'coffee_title': 'Buy me a coffee ☕',
        'coffee_desc': 'Server costs are real. Help keep this alive!',
        'custom_count': 'Custom count (cups)',
        'total_label': 'Total',
        'pay_wechat': 'WeChat',
        'pay_alipay': 'Alipay',
        'pay_paypal': 'PayPal',
        'paid_btn': '🎉 I have paid!',
        'paid_toast': 'Received! Thanks for the {count} coffees! ❤️',
        'coffee_btn': '☕ Support Server',
        'coffee_amount': 'Enter Coffee Count',
        'visitor_today': 'Today UV',
        'visitor_total': 'Total UV',
        'lock_msg': '🔒 Trial Ended',
        'lock_desc': 'Please unlock for full access.',
        'unlock_btn': 'Unlock',
        'more_apps': '✨ More Apps'
    }
}
current_text = lang_texts[st.session_state.language]

# ==========================================
# 5. 辅助函数 (DB & 生成)
# ==========================================
def track_stats():
    """UV/PV 统计逻辑"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT PRIMARY KEY, last_visit_date TEXT)''')
        
        today = datetime.datetime.utcnow().date().isoformat()
        vid = st.session_state["visitor_id"]
        
        if not st.session_state.has_counted:
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today,))
            c.execute("INSERT OR REPLACE INTO visitors (visitor_id, last_visit_date) VALUES (?, ?)", (vid, today))
            conn.commit()
            st.session_state.has_counted = True
        
        t_uv = c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today,)).fetchone()[0]
        a_uv = c.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
        conn.close()
        return t_uv, a_uv
    except:
        return 0, 0

def generate_baby():
    """生成新宝宝数据"""
    city = random.choices(CITY_CHOICES, weights=CITY_WEIGHTS, k=1)[0]
    gender = random.choice(['男孩', '女孩'])
    # 颜色: 男孩青色，女孩粉色 (RGB)
    color = [0, 255, 255, 255] if gender == '男孩' else [255, 105, 180, 255]
    return {
        "city": city['name'],
        "gender": gender,
        "lat": city['lat'],
        "lon": city['lon'],
        "color": color,
        "timestamp": time.time(),
        "id": str(uuid.uuid4())
    }

# ==========================================
# 6. 顶部功能区
# ==========================================
col_empty, col_lang, col_more = st.columns([0.7, 0.1, 0.2])
with col_lang:
    l_btn = "En" if st.session_state.language == 'zh' else "中"
    if st.button(l_btn, key="lang_switch"):
        st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
        st.rerun()

with col_more:
    st.markdown(f"""
        <a href="https://neal.fun/" target="_blank" class="neal-btn-link">
            <button class="neal-btn">{current_text['more_apps']}</button>
        </a>""", unsafe_allow_html=True)

# ==========================================
# 7. 权限校验逻辑 (拦截器)
# ==========================================
current_time = datetime.datetime.now()
access_granted = False

# 检查权限
if st.session_state.access_status == 'free':
    time_elapsed = (current_time - st.session_state.start_time).total_seconds()
    if time_elapsed < FREE_PERIOD_SECONDS:
        access_granted = True
        # 在地图上方显示倒计时
        st.info(f"⏳ 免费体验中... 剩余 {int(FREE_PERIOD_SECONDS - time_elapsed)} 秒")
    else:
        st.session_state.access_status = 'locked'
        st.rerun()
elif st.session_state.access_status == 'unlocked':
    access_granted = True
    st.success("🔓 已解锁完整访问权限")

# 锁定界面
if not access_granted:
    st.error(current_text['lock_msg'])
    st.markdown(f"""
    <div style="background-color: #1f2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; margin-top: 15px; text-align: center;">
        <h3 style="color:white">{current_text['lock_msg']}</h3>
        <p style="color:#9ca3af">{current_text['lock_desc']}</p>
        <code style="background-color: #000; padding: 5px; color: #4ade80; display:block; margin: 10px auto; width: fit-content;">解锁码: {UNLOCK_CODE}</code>
    </div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("lock_form"):
            code = st.text_input("Code", type="password")
            if st.form_submit_button(current_text['unlock_btn'], use_container_width=True):
                if code == UNLOCK_CODE:
                    st.session_state.access_status = 'unlocked'
                    st.rerun()
                else:
                    st.error("Invalid Code")
    st.stop() # 停止后续代码执行

# ==========================================
# 8. 主程序：地图与统计 (权限通过后执行)
# ==========================================
today_uv, total_uv = track_stats()

c_main_1, c_main_2 = st.columns([0.2, 0.8])

# 顶部标题
st.markdown("<h1 style='text-align: center; color: white; margin-bottom: 0;'>👶 中国宝宝地图</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #666; font-size: 0.8rem; margin-bottom: 20px;'>REAL-TIME SIMULATION DATA</div>", unsafe_allow_html=True)

# 占位符容器 (用于动画)
map_container = st.empty()
stats_container = st.empty()

# 底部功能区 (静态)
st.markdown("---")
f_col1, f_col2, f_col3 = st.columns([1, 2, 1])

with f_col2:
    # 底部统计条
    st.markdown(f"""
    <div class="stats-bar">
        <div style="text-align: center;">
            <div>{current_text['visitor_today']}</div>
            <div class="stats-num">{today_uv}</div>
        </div>
        <div style="border-left:1px solid rgba(255,255,255,0.1); padding-left:25px; text-align: center;">
            <div>{current_text['visitor_total']}</div>
            <div class="stats-num">{total_uv}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # 咖啡打赏弹窗
    @st.dialog(current_text['coffee_title'], width="small")
    def show_coffee_window():
        st.markdown(f"""<div class="coffee-card"><p style="font-size:0.9rem;">{current_text['coffee_desc']}</p></div>""", unsafe_allow_html=True)
        
        # 快捷按钮
        presets = [("☕", 1), ("🍗", 3), ("🚀", 10)]
        cols = st.columns(3)
        for i, (icon, num) in enumerate(presets):
            with cols[i]:
                if st.button(f"{icon} {num}", use_container_width=True, key=f"c_btn_{i}"): 
                    st.session_state.coffee_num = num
        
        st.write("")
        c1, c2 = st.columns([1, 1])
        with c1:
            cnt = st.number_input(current_text['custom_count'], 1, 100, step=1, key='coffee_num')
        total = cnt * 10
        with c2:
            st.markdown(f"""<div class="price-tag-container"><div class="price-label">{current_text['total_label']}</div><div class="price-number">¥ {total}</div></div>""", unsafe_allow_html=True)

        # 支付 Tabs
        t1, t2, t3 = st.tabs([current_text['pay_wechat'], current_text['pay_alipay'], current_text['pay_paypal']])
        
        def render_pay(title, amount, img):
            st.markdown(f"""<div class="pay-card"><div class="pay-amount-display">{amount}</div><p class="pay-instruction">请扫码支付</p></div>""", unsafe_allow_html=True)
            # 这里的图片建议替换为真实的 qrcode
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=Pay_{total}", width=150)

        with t1: render_pay("WeChat", f"¥{total}", "wechat.jpg")
        with t2: render_pay("Alipay", f"¥{total}", "alipay.jpg")
        with t3: 
            st.markdown(f"""<div class="pay-card"><div class="pay-amount-display">${cnt*2}</div></div>""", unsafe_allow_html=True)
            st.link_button(f"👉 PayPal Pay ${cnt*2}", "https://paypal.me/yourid", use_container_width=True)

        st.write("")
        if st.button(current_text['paid_btn'], type="primary", use_container_width=True):
            st.balloons()
            st.success(current_text['paid_toast'].format(count=cnt))
            time.sleep(1.5)
            st.rerun()

    # 触发咖啡按钮
    if st.button(current_text['coffee_btn'], use_container_width=True):
        show_coffee_window()


# ==========================================
# 9. 动画循环 (地图逻辑)
# ==========================================
REFRESH_RATE = 0.5 
BIRTH_PROBABILITY = 0.6 # 概率

view_state = pdk.ViewState(
    latitude=35.0,
    longitude=105.0,
    zoom=3.2,
    pitch=0,
)

while True:
    current_ts = time.time()
    
    # 1. 生成新数据
    if random.random() < BIRTH_PROBABILITY:
        new_baby = generate_baby()
        st.session_state.total_born += 1
        
        log_entry = {
            "text": f"{datetime.datetime.now().strftime('%H:%M:%S')} - {new_baby['city']} 迎来了一位{new_baby['gender']}",
            "color": "#40E0D0" if new_baby['gender'] == '男孩' else "#FF69B4"
        }
        st.session_state.born_log.insert(0, log_entry)
        if len(st.session_state.born_log) > 6:
            st.session_state.born_log.pop()
            
        new_row = pd.DataFrame([{
            'lat': new_baby['lat'],
            'lon': new_baby['lon'],
            'color': new_baby['color'],
            'size': 20000, 
            'born_time': current_ts,
            'name': new_baby['city']
        }])
        
        if st.session_state.map_data.empty:
            st.session_state.map_data = new_row
        else:
            st.session_state.map_data = pd.concat([st.session_state.map_data, new_row], ignore_index=True)

    # 2. 清理过期数据 (3秒消失)
    if not st.session_state.map_data.empty:
        st.session_state.map_data = st.session_state.map_data[
            st.session_state.map_data['born_time'] > (current_ts - 3.0)
        ]

    # 3. 渲染 UI (地图 + 实时Log)
    # 注意：stats_container 和 map_container 是在循环外定义的 empty 容器
    with stats_container.container():
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:0.8rem; color:#888; letter-spacing:1px;">本场见证的新生命</div>
                <div class="big-number">{st.session_state.total_born}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 实时日志
        log_html = ""
        for log in st.session_state.born_log:
            log_html += f"<div style='text-align:center; color:{log['color']}; margin-bottom:4px; font-size:14px; font-family: monospace;'>{log['text']}</div>"
        st.markdown(f"<div style='height: 120px; overflow:hidden;'>{log_html}</div>", unsafe_allow_html=True)

    # 4. 渲染地图
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=st.session_state.map_data,
        get_position='[lon, lat]',
        get_color='color',
        get_radius='size',
        pickable=True,
        opacity=0.9,
        filled=True,
        radius_scale=6,
        radius_min_pixels=5,
        radius_max_pixels=40,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=st.session_state.map_data,
        get_position='[lon, lat]',
        get_text='name',
        get_color=[255, 255, 255],
        get_size=14,
        get_alignment_baseline="'bottom'",
        get_text_anchor="'middle'"
    )

    r = pdk.Deck(
        # 使用免 Token 的 CartoDB 暗黑地图
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        layers=[layer, text_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{name}</b>"}
    )
    
    with map_container:
        st.pydeck_chart(r, use_container_width=True)

    time.sleep(REFRESH_RATE)
