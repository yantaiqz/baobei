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
    page_title="China Baby Map | 实时出生模拟",
    page_icon="👶",
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
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }

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
    .stat-box { text-align: center; padding: 0 20px; }
    .stat-val { font-size: 1.8rem; font-weight: 700; color: #4ade80; font-family: 'Courier New', monospace; }
    .stat-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; margin-top: -5px; }

    /* === 实时日志样式 === */
    .log-container {
        height: 150px; overflow-y: hidden;
        mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
        -webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
    }
    .log-item {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem; margin-bottom: 6px;
        text-shadow: 0 0 5px rgba(0,0,0,0.5);
    }

    /* === 咖啡/支付卡片 === */
    .coffee-card {
        background: #1f2937; border: 1px solid #374151;
        border-radius: 12px; padding: 15px; text-align: center; color: white; margin-bottom: 15px;
    }
    .pay-amount { font-size: 2rem; font-weight: 800; color: #f87171; margin: 10px 0; }
    .pay-btn { width: 100%; border-radius: 8px; font-weight: 600; }
    
    /* === 右上角按钮 === */
    .nav-btn {
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.1);
        color: #ddd; padding: 5px 12px; border-radius: 20px; cursor: pointer;
        font-size: 0.8rem; text-decoration: none; display: inline-block;
    }
    .nav-btn:hover { background: rgba(255,255,255,0.2); color: white; }
    
    /* Streamlit 元素微调 */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心数据 (省份 + 语言包)
# ==========================================

# 省份坐标与人口权重 (2023近似数据)
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
        'title': '中国宝宝地图',
        'subtitle': '实时模拟数据 | 基于各省人口权重',
        'born_count': '本场见证新生',
        'uv_today': '今日访客',
        'uv_total': '累计访客',
        'log_boy': '{time} - {prov} 迎来了一位男孩',
        'log_girl': '{time} - {prov} 迎来了一位女孩',
        'coffee_title': '请开发者喝咖啡',
        'coffee_desc': '如果这些工具帮到了你，欢迎支持老登的创作！',
        'custom_cups': '自定义数量',
        'total_label': '总金额',
        'btn_pay': '我已支付，确认支持',
        'toast_thanks': '收到！感谢您的 {count} 杯咖啡！❤️',
        'lock_title': '免费体验结束',
        'lock_msg': '请解锁以继续观看实时数据。',
        'unlock_btn': '验证并解锁',
        'pay_wechat': '微信支付',
        'pay_alipay': '支付宝',
        'pay_paypal': '贝宝',
        'more_app': '更多应用',

        'paid_btn': '🎉 我已支付，给老登打气！',
        'paid_toast': '收到！感谢你的 {count} 杯咖啡！代码写得更有劲了！❤️',
        'presets': [("☕ 提神", "由衷感谢"), ("🍗 鸡腿", "动力加倍"), ("🚀 续命", "老登不朽")],
        "coffee_btn": "☕ 请开发者喝咖啡",
        "coffee_title": " ",
        "pay_success": "收到！感谢打赏。代码写得更有劲了！❤️",
        "coffee_amount": "请输入打赏杯数"

        
    },
    'en': {
        'title': 'China Baby Map',
        'subtitle': 'Real-time Simulation based on Population',
        'born_count': 'Babies Born',
        'uv_today': 'Today Visitors',
        'uv_total': 'Total Visitors',
        'log_boy': '{time} - {prov} welcomed a baby boy',
        'log_girl': '{time} - {prov} welcomed a baby girl',
        'coffee_title': 'Buy me a coffee',
        'coffee_desc': 'Help keep the server running!',
        'custom_cups': 'Custom Cups',
        'total_label': 'Total Amount',
        'btn_pay': 'I have paid',
        'toast_thanks': 'Received! Thanks for {count} coffees! ❤️',
        'lock_title': 'Trial Ended',
        'lock_msg': 'Please unlock to view real-time data.',
        'unlock_btn': 'Unlock',
        'pay_wechat': 'WeChat',
        'pay_alipay': 'Alipay',
        'pay_paypal': 'PayPal',
        'more_app': 'More Apps',
        
        'paid_btn': '🎉 I have paid!',
        'paid_toast': 'Received! Thanks for the {count} coffees! ❤️',
        'presets': [("☕ Coffee", "Thanks"), ("🍗 Meal", "Power Up"), ("🚀 Rocket", "Amazing")],
        "coffee_btn": "☕ Buy me a coffee",
        "coffee_title": " ",
        "coffee_desc": "If you enjoyed this, consider buying me a coffee!",
        "pay_success": "Received! Thanks for the coffee! ❤️",
        "coffee_amount": "Enter Coffee Count"
    }
}

# ==========================================
# 3. 状态管理
# ==========================================
def init_session():
    defaults = {
        'start_time': datetime.datetime.now(),
        'access_status': 'free',
        'language': 'zh',
        'coffee_num': 1,
        'visitor_id': str(uuid.uuid4()),
        'has_counted': False,
        'total_born': 0,
        'born_log': [],
        'map_data': pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name'])
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()
TXT = TEXTS[st.session_state.language]
    
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
            c.execute("INSERT OR IGNORE INTO stats VALUES ('global', 'uv', 0)")
            c.execute("UPDATE stats SET val = val + 1 WHERE type='uv'")
            conn.commit()
            st.session_state.has_counted = True
        
        c.execute("SELECT val FROM stats WHERE date=? AND type='pv'", (today,))
        d_pv = c.fetchone()
        c.execute("SELECT val FROM stats WHERE type='uv'")
        t_uv = c.fetchone()
        conn.close()
        return d_pv[0] if d_pv else 1, t_uv[0] if t_uv else 1
    except: return 0, 0

def generate_baby():
    """生成新数据"""
    prov = random.choices(PROVINCES, weights=PROV_WEIGHTS, k=1)[0]
    gender = random.choice(['m', 'f'])
    # 颜色: 男孩青蓝(0, 255, 255), 女孩洋红(255, 0, 255)
    color = [0, 255, 255, 200] if gender == 'm' else [255, 0, 255, 200]
    
    return {
        "zh": prov["zh"],
        "en": prov["en"],
        "gender": gender,
        "lat": prov['lat'],
        "lon": prov['lon'],
        "color": color,
    }

# ==========================================
# 5. UI: 顶部 HUD
# ==========================================
today_pv, total_uv = track_stats()

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
    # 语言切换 & 外链
    cols = st.columns([1, 1, 1])
    with cols[1]:
        lang_btn = "🌐 EN" if st.session_state.language == 'zh' else "🌐 中"
        if st.button(lang_btn, use_container_width=True):
            st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
            st.rerun()
    with cols[2]:
        st.markdown(f'<a href="https://laodeng.streamlit.app" target="_blank" class="nav-btn" style="text-align:center; width:100%; padding: 8px 0;">{TXT["more_app"]} ↗</a>', unsafe_allow_html=True)


# ==========================================
# 7. 主界面 (地图 + 统计)
# ==========================================
map_placeholder = st.empty()
stats_placeholder = st.empty()


# ==========================================
# 8. 新版咖啡打赏逻辑 (替换旧版)
# ==========================================

def get_txt(key): 
    return TEXTS[st.session_state.language][key]

#st.markdown("<br><br>", unsafe_allow_html=True)    
c1, c2, c3 = st.columns([1, 2, 1])

with c2:
    @st.dialog(" " + get_txt('coffee_title'), width="small")
    def show_coffee_window():
        # 1. 顶部描述
        st.markdown(f"""<div style="text-align:center; color:#666; margin-bottom:15px;">{get_txt('coffee_desc')}</div>""", unsafe_allow_html=True)
        
        # 2. 快捷选择按钮
        presets = [("☕", 1), ("🍗", 3), ("🚀", 5)]
        def set_val(n):
            st.session_state.coffee_num = n
            st.rerun()
            print(f"当前咖啡杯数：{st.session_state.coffee_num}")
        
        cols = st.columns(3, gap="small")
        for i, (icon, num) in enumerate(presets):
            with cols[i]:
                # 点击快捷键直接修改 session_state
                if st.button(f"{icon} {num}", use_container_width=True, key=f"p_btn_{i}"): 
                    set_val(num)
                    
        st.write("")

        # 3. 自定义输入与金额计算
        col_amount, col_total = st.columns([1, 1], gap="small")
        with col_amount: 
            cnt = st.number_input(get_txt('coffee_amount'), 1, 100, step=1, key='coffee_num')
        
        # 汇率计算逻辑
        cny_total = cnt * 10
        usd_total = cnt * 2
        
        # 4. 统一支付卡片渲染函数 (核心复用逻辑)
        def render_pay_tab(title, amount_str, color_class, img_path, qr_data_suffix, link_url=None):
            # 使用 st.container 并开启 border 边框
            with st.container(border=True):
                # 卡片头部 (包含支付名称和金额)
                st.markdown(f"""
                    <div style="text-align: center; padding-bottom: 10px;">
                        <div class="pay-label {color_class}" style="margin-bottom: 5px;">{title}</div>
                        <div class="pay-amount-display {color_class}" style="margin: 0; font-size: 1.8rem;">{amount_str}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 卡片中部：二维码或图片
                # 调整列比例让图片在边框内更协调
                c_img_1, c_img_2, c_img_3 = st.columns([1, 4, 1])
                with c_img_2:
                    if os.path.exists(img_path): 
                        st.image(img_path, use_container_width=True)
                    else: 
                        # 本地图片不存在时，生成 API 二维码作为演示
                        qr_data = f"Donate_{cny_total}_{qr_data_suffix}"
                        # PayPal 如果是链接模式，二维码也可以指向链接
                        if link_url: qr_data = link_url
                        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={qr_data}", use_container_width=True)
                
                # 卡片底部：按钮或提示文字
                if link_url:
                    # PayPal 等外链跳转
                    st.write("") # 增加一点间距
                    st.link_button(f"👉 Pay {amount_str}", link_url, type="primary", use_container_width=True)
                else:
                    # 扫码提示
                    st.markdown(f"""
                        <div class="pay-instruction" style="text-align: center; padding-top: 10px;">
                            请使用手机扫描上方二维码
                        </div>
                    """, unsafe_allow_html=True)
                    
            
        # 5. 支付方式 Tabs
        st.write("")
        t1, t2, t3 = st.tabs([get_txt('pay_wechat'), get_txt('pay_alipay'), get_txt('pay_paypal')])
        
        with t1:
            render_pay_tab("WeChat Pay", f"¥{cny_total}", "color-wechat", "wechat_pay.jpg", "WeChat")
            
        with t2:
            render_pay_tab("Alipay", f"¥{cny_total}", "color-alipay", "ali_pay.jpg", "Alipay")
            
        with t3:
            # PayPal 特殊处理：提供 URL 跳转
            render_pay_tab("PayPal", f"${usd_total}", "color-paypal", "paypal.png", "PayPal", "https://paypal.me/ytqz")
        
        # 6. 确认按钮
        st.write("")
        if st.button("🎉 " + get_txt('pay_success').split('!')[0], type="primary", use_container_width=True):
            st.balloons()
            st.success(get_txt('pay_success').format(count=cnt))
            time.sleep(1.5)
            st.rerun()

    # 主界面触发按钮
    if st.button(get_txt('coffee_btn'), use_container_width=True):
        show_coffee_window()


        
# ==========================================
# 8. 动画主循环
# ==========================================
# 视图配置
view_state = pdk.ViewState(latitude=35.0, longitude=105.0, zoom=3.2, pitch=20)
REFRESH_RATE = 0.8
BIRTH_PROB = 0.6

while True:
    ts = time.time()
    
    # 1. 生成新宝宝
    if random.random() < BIRTH_PROB:
        baby = generate_baby()
        st.session_state.total_born += 1
        
        # 生成日志文本
        t_str = datetime.datetime.now().strftime('%H:%M:%S')
        prov_name = baby['zh'] if st.session_state.language == 'zh' else baby['en']
        
        if st.session_state.language == 'zh':
            gender_txt = "男孩" if baby['gender'] == 'm' else "女孩"
            log_txt = TXT['log_boy' if baby['gender']=='m' else 'log_girl'].format(time=t_str, prov=prov_name)
        else:
            gender_txt = "boy" if baby['gender'] == 'm' else "girl"
            log_txt = TXT['log_boy' if baby['gender']=='m' else 'log_girl'].format(time=t_str, prov=prov_name)
            
        st.session_state.born_log.insert(0, {"t": log_txt, "c": baby['color']})
        if len(st.session_state.born_log) > 8: st.session_state.born_log.pop()
        
        # 添加地图点
        new_row = pd.DataFrame([{
            'lat': baby['lat'], 'lon': baby['lon'],
            'color': baby['color'], 'size': 30000, 
            'born_time': ts, 'name': prov_name
        }])
        
        if st.session_state.map_data.empty:
            st.session_state.map_data = new_row
        else:
            st.session_state.map_data = pd.concat([st.session_state.map_data, new_row], ignore_index=True)

    # 2. 清理过期数据 (2.5秒消失)
    if not st.session_state.map_data.empty:
        st.session_state.map_data = st.session_state.map_data[
            st.session_state.map_data['born_time'] > (ts - 2.5)
        ]

    # 3. 渲染统计区 (HUD)
    with stats_placeholder.container():
        c1, c2, c3 = st.columns([1, 1, 1])
        
        # 左侧数字
        with c1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-val">{st.session_state.total_born}</div>
                <div class="stat-label">{TXT['born_count']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # 中间/右侧日志
        with c2:
            logs_html = ""
            for log in st.session_state.born_log[:5]:
                # 颜色处理
                color_css = "#22d3ee" if log['c'][0] == 0 else "#e879f9" # 青 vs 粉
                logs_html += f'<div class="log-item" style="color:{color_css}">{log["t"]}</div>'
            st.markdown(f'<div class="log-container">{logs_html}</div>', unsafe_allow_html=True)

    # 4. 渲染地图
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=st.session_state.map_data,
        get_position='[lon, lat]',
        get_fill_color='color',
        get_radius='size',
        pickable=False,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=6,
        radius_min_pixels=5,
        radius_max_pixels=60,
        get_line_color=[255, 255, 255, 100],
        get_line_width=2000,
    )
    
    # 增加省份文字层
    text_layer = pdk.Layer(
        "TextLayer",
        data=st.session_state.map_data,
        get_position='[lon, lat]',
        get_text='name',
        get_color=[255, 255, 255],
        get_size=15,
        get_alignment_baseline="'bottom'",
        get_text_anchor="'middle'"
    )

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        layers=[layer, text_layer],
        initial_view_state=view_state,
        tooltip=False
    )
    
    with map_placeholder:
        st.pydeck_chart(deck, use_container_width=True)

    time.sleep(REFRESH_RATE)
