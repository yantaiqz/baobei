import streamlit as st
import pydeck as pdk
import pandas as pd
import time
import random
import datetime
import uuid

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(
    page_title="中国宝宝地图 | China Baby Map",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === CSS 样式优化 (暗黑霓虹风) ===
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background-color: #0e1117;
    }
    
    /* 隐藏顶部Header和Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    
    /* 统计卡片样式 */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
    .big-number {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(#eee, #999);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Arial', sans-serif;
    }
    .label {
        font-size: 0.9rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 地理数据
# ==========================================
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
    {"name": "哈尔滨", "lat": 45.8038, "lon": 126.5350, "weight": 9},
    {"name": "乌鲁木齐", "lat": 43.8256, "lon": 87.6168, "weight": 4},
    {"name": "昆明", "lat": 24.8801, "lon": 102.8329, "weight": 8},
    {"name": "拉萨", "lat": 29.6525, "lon": 91.1721, "weight": 1},
    {"name": "兰州", "lat": 36.0611, "lon": 103.8343, "weight": 4},
    {"name": "海口", "lat": 20.0174, "lon": 110.3492, "weight": 3},
]

CITY_CHOICES = []
CITY_WEIGHTS = []
for c in CITIES:
    CITY_CHOICES.append(c)
    CITY_WEIGHTS.append(c['weight'])

# ==========================================
# 3. 状态管理
# ==========================================
if 'total_born' not in st.session_state:
    st.session_state.total_born = 0
if 'born_log' not in st.session_state:
    st.session_state.born_log = [] 
if 'map_data' not in st.session_state:
    st.session_state.map_data = pd.DataFrame(columns=['lat', 'lon', 'color', 'size', 'name'])

# ==========================================
# 4. 辅助函数
# ==========================================
def generate_baby():
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
# 5. 页面布局
# ==========================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    st.markdown("<h1 style='text-align: center; color: white;'>👶 中国宝宝地图</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 0.8rem;'>演示数据：模拟实时出生概率</p>", unsafe_allow_html=True)

# 占位符
map_container = st.empty()
stats_container = st.empty()

# ==========================================
# 6. 动画主循环
# ==========================================
REFRESH_RATE = 0.5 
BIRTH_PROBABILITY = 0.5

view_state = pdk.ViewState(
    latitude=35.0,
    longitude=105.0,
    zoom=3,
    pitch=0,
)

while True:
    current_time = time.time()
    
    # 1. 生成
    if random.random() < BIRTH_PROBABILITY:
        new_baby = generate_baby()
        st.session_state.total_born += 1
        
        log_entry = {
            "text": f"{datetime.datetime.now().strftime('%H:%M:%S')} - {new_baby['city']} 迎来了一位{new_baby['gender']}",
            "color": "#40E0D0" if new_baby['gender'] == '男孩' else "#FF69B4"
        }
        st.session_state.born_log.insert(0, log_entry)
        if len(st.session_state.born_log) > 5:
            st.session_state.born_log.pop()
            
        new_row = pd.DataFrame([{
            'lat': new_baby['lat'],
            'lon': new_baby['lon'],
            'color': new_baby['color'],
            'size': 20000, 
            'born_time': current_time,
            'name': new_baby['city']
        }])
        
        if st.session_state.map_data.empty:
            st.session_state.map_data = new_row
        else:
            st.session_state.map_data = pd.concat([st.session_state.map_data, new_row], ignore_index=True)

    # 2. 清理 (移除超过3秒的数据)
    if not st.session_state.map_data.empty:
        st.session_state.map_data = st.session_state.map_data[
            st.session_state.map_data['born_time'] > (current_time - 3.0)
        ]

    # 3. 渲染 UI
    with stats_container.container():
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">本场见证的新生命</div>
                <div class="big-number">{st.session_state.total_born}</div>
            </div>
            """, unsafe_allow_html=True)
        
        log_html = ""
        for log in st.session_state.born_log:
            log_html += f"<div style='text-align:center; color:{log['color']}; margin-bottom:4px; font-size:14px; font-family: monospace;'>{log['text']}</div>"
        
        st.markdown(f"<div style='height: 100px; overflow:hidden;'>{log_html}</div>", unsafe_allow_html=True)

    # 4. 渲染地图 (修复版：使用 CartoDB)
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
        # 核心修改：使用 CartoDB Dark Matter 样式，无需 Token
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        layers=[layer, text_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{name}</b>"}
    )
    
    with map_container:
        st.pydeck_chart(r, use_container_width=True)

    time.sleep(REFRESH_RATE)
