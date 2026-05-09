import os
import streamlit as st
from PIL import Image
import io
from dotenv import load_dotenv

from analyzer import analyze_room
from floorplan import generate_floor_plan

load_dotenv()

st.set_page_config(
    page_title="CHIFU 房間格局分析器",
    page_icon="🏠",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-header { font-size: 2rem; font-weight: 700; color: #2C3E50; margin-bottom: 0.2rem; }
    .sub-header { color: #7F8C8D; font-size: 1rem; margin-bottom: 1.5rem; }
    .result-box { background: #F8F9FA; border-radius: 10px; padding: 1rem 1.5rem; margin: 0.5rem 0; }
    .confidence-high { color: #27AE60; font-weight: bold; }
    .confidence-medium { color: #F39C12; font-weight: bold; }
    .confidence-low { color: #E74C3C; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">🏠 CHIFU 房間格局分析器</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">上傳房間磁磚地板照片，AI 自動估算尺寸並生成俯視平面圖</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ 設定")

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="輸入您的 Anthropic API Key，或設定環境變數 ANTHROPIC_API_KEY",
    )

    st.divider()

    st.subheader("磁磚尺寸")
    use_manual_tile = st.checkbox("手動輸入磁磚尺寸", value=False)

    tile_width_cm = None
    tile_height_cm = None

    if use_manual_tile:
        col1, col2 = st.columns(2)
        with col1:
            tile_width_cm = st.number_input(
                "寬度 (cm)", min_value=1.0, max_value=200.0, value=60.0, step=0.5
            )
        with col2:
            tile_height_cm = st.number_input(
                "高度 (cm)", min_value=1.0, max_value=200.0, value=60.0, step=0.5
            )

        common_sizes = {
            "30×30 cm": (30, 30),
            "60×60 cm": (60, 60),
            "30×60 cm": (30, 60),
            "45×45 cm": (45, 45),
            "80×80 cm": (80, 80),
        }
        selected = st.selectbox("或選擇常見尺寸", ["自訂"] + list(common_sizes.keys()))
        if selected != "自訂":
            tile_width_cm, tile_height_cm = common_sizes[selected]
    else:
        st.info("將由 AI 根據照片估算磁磚尺寸")

    st.divider()
    st.caption("使用 Claude claude-sonnet-4-6 視覺分析")


col_upload, col_result = st.columns([1, 1], gap="large")

with col_upload:
    st.subheader("📷 上傳照片")
    uploaded_file = st.file_uploader(
        "選擇房間照片",
        type=["jpg", "jpeg", "png", "webp"],
        help="建議使用能清楚看到地板磁磚的照片，站立角度拍攝效果最佳",
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳照片", use_container_width=True)

        st.markdown(
            """
            **拍攝建議：**
            - 站立視角，俯角約 45°
            - 確保地板磁磚清晰可見
            - 盡量拍攝整個房間範圍
            - 光線充足，避免陰影遮蓋磁磚
            """
        )

    analyze_btn = st.button(
        "🔍 開始分析",
        type="primary",
        disabled=not uploaded_file,
        use_container_width=True,
    )

with col_result:
    st.subheader("📐 分析結果")

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
        st.session_state.floor_plan_image = None
        st.session_state.last_filename = None

    if analyze_btn and uploaded_file:
        effective_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not effective_api_key:
            st.error("請在側邊欄輸入 Anthropic API Key，或設定 ANTHROPIC_API_KEY 環境變數。")
        else:
            with st.spinner("AI 正在分析照片中的磁磚格局..."):
                try:
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()

                    media_type_map = {
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "png": "image/png",
                        "webp": "image/webp",
                    }
                    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
                    media_type = media_type_map.get(ext, "image/jpeg")

                    analysis = analyze_room(
                        image_bytes=image_bytes,
                        image_media_type=media_type,
                        tile_width_cm=tile_width_cm if use_manual_tile else None,
                        tile_height_cm=tile_height_cm if use_manual_tile else None,
                        api_key=effective_api_key,
                    )

                    floor_plan_bytes = generate_floor_plan(analysis)

                    st.session_state.analysis_result = analysis
                    st.session_state.floor_plan_image = floor_plan_bytes
                    st.session_state.last_filename = uploaded_file.name

                except Exception as e:
                    st.error(f"分析失敗：{e}")

    if st.session_state.analysis_result:
        analysis = st.session_state.analysis_result

        st.image(st.session_state.floor_plan_image, caption="房間格局俯視圖", use_container_width=True)

        st.download_button(
            label="⬇️ 下載俯視圖 (PNG)",
            data=st.session_state.floor_plan_image,
            file_name="room_floor_plan.png",
            mime="image/png",
            use_container_width=True,
        )

        st.markdown("---")

        shape_labels = {
            "rectangular": "矩形",
            "L-shaped": "L 形",
            "U-shaped": "U 形",
            "irregular": "不規則形",
        }
        shape = shape_labels.get(analysis.get("room_shape", ""), analysis.get("room_shape", ""))

        conf = analysis.get("confidence", "medium")
        conf_labels = {"high": "高 ✅", "medium": "中 ⚠️", "low": "低 ❌"}
        conf_label = conf_labels.get(conf, conf)
        conf_css = f"confidence-{conf}"

        total_area = sum(
            seg["tiles_x"] * analysis["tile_width_cm"] / 100 *
            seg["tiles_y"] * analysis["tile_height_cm"] / 100
            for seg in analysis["segments"]
        )

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("房間形狀", shape)
        with metric_cols[1]:
            st.metric("估算面積", f"{total_area:.1f} m²")
        with metric_cols[2]:
            st.metric("信心度", conf_label)

        st.markdown("**磁磚資訊**")
        tile_source = "使用者提供" if analysis.get("tile_estimation_source") == "user_provided" else "AI 估算"
        st.markdown(
            f"""
            <div class="result-box">
            尺寸：<b>{analysis['tile_width_cm']:.0f} × {analysis['tile_height_cm']:.0f} cm</b>
            來源：{tile_source}
            {f"<br><small>{analysis.get('tile_estimation_note', '')}</small>" if analysis.get('tile_estimation_note') else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**各區域尺寸**")
        for seg in analysis["segments"]:
            w_cm = seg["tiles_x"] * analysis["tile_width_cm"]
            h_cm = seg["tiles_y"] * analysis["tile_height_cm"]
            st.markdown(
                f"""
                <div class="result-box">
                <b>{seg.get('name', '區域')}</b>：
                {w_cm:.0f} cm × {h_cm:.0f} cm
                （{seg['tiles_x']} × {seg['tiles_y']} 塊磁磚）
                </div>
                """,
                unsafe_allow_html=True,
            )

        if analysis.get("analysis_notes"):
            with st.expander("📋 AI 分析說明"):
                st.write(analysis["analysis_notes"])
                if analysis.get("camera_angle"):
                    st.write(f"**拍攝角度：** {analysis['camera_angle']}")
    else:
        st.markdown(
            """
            <div style="text-align:center; color:#BDC3C7; padding: 3rem 0;">
                <div style="font-size:4rem;">🏠</div>
                <div style="font-size:1.1rem; margin-top:1rem;">上傳照片後點擊「開始分析」</div>
                <div style="font-size:0.85rem; margin-top:0.5rem;">AI 將自動分析磁磚格局並生成俯視圖</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
