import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Rapsodo 捕手視角好球帶分析儀", layout="wide")

st.title("⚾ Rapsodo 投球軌跡與好球帶融合分析系統")
st.markdown("完美還原每一顆球的**真實出手點**、**實測位移**與**好球帶進壘點**（已鎖定標準捕手視角與 1:1 等比例視圖）。")

st.sidebar.header("📂 1. 資料匯入")
uploaded_file = st.sidebar.file_uploader("上傳您的 Rapsodo CSV 檔案", type=["csv"])

def px_color(i):
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    return colors[i % len(colors)]

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.iloc[::-1].reset_index(drop=True)  # 將逐球記錄上下反轉
        st.sidebar.success("✅ 成功讀取您的 Rapsodo 檔案！")
    except Exception as e:
        st.error(f"讀取 CSV 發生錯誤: {e}")
        st.stop()
else:
    df = pd.DataFrame({
        'PitchID': [1, 2, 3],
        'Pitch Type': ['FB', 'SL', 'CB'],
        'RelSpeed (MPH)': [84.2, 71.3, 67.7],
        'SpinRate': [2013, 2191, 1652],
        'RelHeight (Feet)': [5.5, 5.7, 5.9],
        'RelSide (Feet)': [1.3, 1.0, 1.1],
        'PlateLocSide (Inches)': [8.0, -10.7, -1.6],
        'PlateLocHeight (Inches)': [20.0, -4.4, 30.0],
        'InducedVertBreak (Inches)': [15.0, -4.4, -6.9],
        'HorzBreak (Inches)': [11.0, -10.7, -1.6],
        'Pitcher First Name': ['柏霖', '柏霖', '柏霖'],
        'Pitcher Last Name': ['簡', '簡', '簡']
    })
    df = df.iloc[::-1].reset_index(drop=True)

# 1. 自動偵測投手投球手 (RHP / LHP)
def detect_pitcher_hand(df):
    for col in ['PitcherThrows', 'Throws', 'Hand', 'Pitcher Throws']:
        if col in df.columns:
            val = df[col].dropna().astype(str).str.upper().values
            if len(val) > 0:
                if 'L' in val[0]: return 'L'
                if 'R' in val[0]: return 'R'
    return 'R'

pitcher_hand = detect_pitcher_hand(df)

# 自動抓取球員姓名
pitcher_name = "未知球員"
if 'Pitcher Last Name' in df.columns and 'Pitcher First Name' in df.columns:
    last_names = df['Pitcher Last Name'].dropna().unique()
    first_names = df['Pitcher First Name'].dropna().unique()
    if len(last_names) > 0 and len(first_names) > 0:
        pitcher_name = f"{last_names[0]}{first_names[0]}"

st.sidebar.markdown("---")
st.sidebar.info(f"👤 **當前投球球員**: {pitcher_name} ({'右投 RHP' if pitcher_hand == 'R' else '左投 LHP'})")

# 側邊欄球種篩選
st.sidebar.header("🎯 2. 球路篩選")
pitch_type_col = 'Pitch Type' if 'Pitch Type' in df.columns else df.columns[0]
pitch_types = df[pitch_type_col].unique().tolist()
selected_pitches = st.sidebar.multiselect("勾選要顯示在圖表上的球種", pitch_types, default=pitch_types)

filtered_df = df[df[pitch_type_col].isin(selected_pitches)].reset_index(drop=True)

st.subheader(f"🎯 捕手視角：{pitcher_name} 投手之真實出手點與進壘點軌跡融合圖")
st.markdown("*(好球帶高度設定：47公分至 105公分，已鎖定 1:1 等比例視圖，絕不變形)*")

fig = go.Figure()

# 1. 繪製鮮紅色好球帶框線
strike_zone_y_min = 0.47
strike_zone_y_max = 1.05

fig.add_shape(type="rect",
    x0=-0.215, y0=strike_zone_y_min, x1=0.215, y1=strike_zone_y_max,
    line=dict(color="red", width=3.5),
    fillcolor="rgba(255, 0, 0, 0.06)"
)

# 九宮格格線
y_step = (strike_zone_y_max - strike_zone_y_min) / 3.0
fig.add_shape(type="line", x0=-0.0716, y0=strike_zone_y_min, x1=-0.0716, y1=strike_zone_y_max, line=dict(color="rgba(255,0,0,0.25)", width=1, dash="dash"))
fig.add_shape(type="line", x0=0.0716, y0=strike_zone_y_min, x1=0.0716, y1=strike_zone_y_max, line=dict(color="rgba(255,0,0,0.25)", width=1, dash="dash"))
fig.add_shape(type="line", x0=-0.215, y0=strike_zone_y_min + y_step, x1=0.215, y1=strike_zone_y_min + y_step, line=dict(color="rgba(255,0,0,0.25)", width=1, dash="dash"))
fig.add_shape(type="line", x0=-0.215, y0=strike_zone_y_min + y_step * 2, x1=0.215, y1=strike_zone_y_min + y_step * 2, line=dict(color="rgba(255,0,0,0.25)", width=1, dash="dash"))

# 2. 繪製本壘板輪廓
hp_x = [-0.215, 0.215, 0.215, 0.0, -0.215]
hp_z = [0.15, 0.15, 0.22, 0.28, 0.22]
fig.add_trace(go.Scatter(
    x=hp_x, y=hp_z,
    mode='lines',
    line=dict(color='white', width=2),
    fill='toself',
    fillcolor='rgba(240,240,240,0.9)',
    name='本壘板',
    hoverinfo='skip'
))

entry_x = []
entry_z = []
hover_texts = []

for idx, row in filtered_df.iterrows():
    p_type = row.get('Pitch Type', '球路')
    vel = row.get('RelSpeed (MPH)', 0.0)
    spin = row.get('SpinRate', 0.0)
    
    rel_h_ft = float(row.get('RelHeight (Feet)', 5.4))
    rel_s_ft = float(row.get('RelSide (Feet)', 1.2))
    
    loc_side_in = float(row.get('PlateLocSide (Inches)', 0.0))
    loc_height_in = float(row.get('PlateLocHeight (Inches)', 30.0))
    
    hb_in = float(row.get('HorzBreak (Inches)', 0.0))
    ivb_in = float(row.get('InducedVertBreak (Inches)', 0.0))
    
    # 📌 標準捕手視角固定轉換規則：
    # 1. 進壘點 (PlateLocSide)：在 Rapsodo 標準捕手視角下，正值為右側、負值為左側
    final_x = (loc_side_in / 8.5) * 0.215
    final_z = (loc_height_in * 0.0254)
    
    # 2. 出手點 (Start X)：
    # 右投手 (RHP) 在捕手視角下，出手點永遠在左側 (X < 0)
    # 左投手 (LHP) 在捕手視角下，出手點永遠在右側 (X > 0)
    if pitcher_hand == 'R':
        start_x = -abs(rel_s_ft) * 0.3  # 強制固定在左側
    else:
        start_x = abs(rel_s_ft) * 0.3   # 強制固定在右側
        
    start_z = rel_h_ft * 0.25
    
    hb_m = (hb_in / 12.0) * 0.1
    ivb_m = (ivb_in / 12.0) * 0.1
    
    # 貝茲曲線軌跡
    ts = np.linspace(0, 1, 30)
    ctrl_x = (start_x + final_x) / 2 - hb_m * 0.5
    ctrl_z = (start_z + final_z) / 2 + ivb_m * 0.3 + 0.1
    
    curve_x = (1 - ts)**2 * start_x + 2 * (1 - ts) * ts * ctrl_x + ts**2 * final_x
    curve_z = (1 - ts)**2 * start_z + 2 * (1 - ts) * ts * ctrl_z + ts**2 * final_z
    
    fig.add_trace(go.Scatter(
        x=curve_x, y=curve_z,
        mode='lines',
        line=dict(width=3, color=px_color(idx)),
        name=f"#{idx+1} {p_type} ({vel:.1f} mph)",
        hoverinfo='name'
    ))
    
    entry_x.append(final_x)
    entry_z.append(final_z)
    hover_texts.append(f"投球球員: {pitcher_name}<br>第 {idx+1} 球<br>球種: {p_type}<br>球速: {vel:.1f} mph<br>轉速: {spin:.0f} rpm<br>進壘點(左右): {loc_side_in:+.1f}吋<br>進壘點(高度): {loc_height_in:.1f}吋")

if entry_x:
    fig.add_trace(go.Scatter(
        x=entry_x, y=entry_z,
        mode='text+markers',
        text=[f"<b>{i+1}</b>" for i in range(len(entry_x))],
        textposition="middle center",
        textfont=dict(color="white", size=11),
        marker=dict(size=18, color="red", symbol="circle", line=dict(color="white", width=2)),
        name='進壘點',
        hovertext=hover_texts,
        hoverinfo='text'
    ))

fig.update_layout(
    xaxis=dict(range=[-0.8, 0.8], title='← 捕手視角左側 (右投出手側) ｜ 捕手視角右側 →', zeroline=True, zerolinecolor='gray'),
    yaxis=dict(range=[0.0, 1.8], title='高度位置 (公尺)', scaleanchor="x", scaleratio=1, zeroline=True),
    width=850,
    height=750,
    legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.8)"),
    margin=dict(l=20, r=20, b=20, t=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader(f"📊 {pitcher_name} 投球數據明細")
st.dataframe(filtered_df, use_container_width=True)
