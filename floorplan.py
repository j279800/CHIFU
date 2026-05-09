import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import numpy as np


def _draw_dimension_arrow(ax, x1, y1, x2, y2, label, offset=0.3, color="#333333"):
    """Draw a dimension line with arrows and a label."""
    is_horizontal = abs(y2 - y1) < abs(x2 - x1)

    if is_horizontal:
        oy, ox = offset, 0
        mx, my = (x1 + x2) / 2, y1 + oy + 0.1
    else:
        ox, oy = offset, 0
        mx, my = x1 + ox + 0.1, (y1 + y2) / 2

    ax.annotate(
        "",
        xy=(x2 + ox, y2 + oy),
        xytext=(x1 + ox, y1 + oy),
        arrowprops=dict(arrowstyle="<->", color=color, lw=1.5),
    )
    ax.text(
        mx,
        my,
        label,
        ha="center",
        va="bottom" if is_horizontal else "center",
        fontsize=9,
        color=color,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8),
    )


def generate_floor_plan(analysis: dict) -> bytes:
    tile_w = analysis["tile_width_cm"] / 100
    tile_h = analysis["tile_height_cm"] / 100
    segments = analysis["segments"]

    fig, ax = plt.subplots(1, 1, figsize=(10, 9))
    ax.set_aspect("equal")

    all_x, all_y = [], []
    colors = ["#E8F4F8", "#EAF4EA", "#FFF8E7", "#F3E8F8"]

    for i, seg in enumerate(segments):
        ox = seg["offset_x"] * tile_w
        oy = seg["offset_y"] * tile_h
        w = seg["tiles_x"] * tile_w
        h = seg["tiles_y"] * tile_h

        rect = patches.Rectangle(
            (ox, oy), w, h,
            linewidth=2,
            edgecolor="#2C3E50",
            facecolor=colors[i % len(colors)],
        )
        ax.add_patch(rect)

        for gx in np.arange(ox, ox + w + 0.001, tile_w):
            ax.plot([gx, gx], [oy, oy + h], color="#AABCCC", lw=0.4, alpha=0.7)
        for gy in np.arange(oy, oy + h + 0.001, tile_h):
            ax.plot([ox, ox + w], [gy, gy], color="#AABCCC", lw=0.4, alpha=0.7)

        all_x.extend([ox, ox + w])
        all_y.extend([oy, oy + h])

        label_x = ox + w / 2
        label_y = oy + h / 2
        ax.text(
            label_x, label_y,
            seg.get("name", f"區域 {i+1}"),
            ha="center", va="center",
            fontsize=10, color="#34495E", alpha=0.6,
        )

    margin = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) * 0.25
    dim_offset = margin * 0.5

    for i, seg in enumerate(segments):
        ox = seg["offset_x"] * tile_w
        oy = seg["offset_y"] * tile_h
        w = seg["tiles_x"] * tile_w
        h = seg["tiles_y"] * tile_h

        w_cm = seg["tiles_x"] * analysis["tile_width_cm"]
        h_cm = seg["tiles_y"] * analysis["tile_height_cm"]

        dim_y_offset = -(dim_offset * (0.5 + i * 0.5))
        _draw_dimension_arrow(
            ax,
            ox, oy + dim_y_offset,
            ox + w, oy + dim_y_offset,
            f"{w_cm:.0f} cm",
            offset=0,
        )

        dim_x_offset = -(dim_offset * (0.5 + i * 0.5))
        _draw_dimension_arrow(
            ax,
            ox + dim_x_offset, oy,
            ox + dim_x_offset, oy + h,
            f"{h_cm:.0f} cm",
            offset=0,
        )

    total_area = sum(
        seg["tiles_x"] * analysis["tile_width_cm"] / 100 *
        seg["tiles_y"] * analysis["tile_height_cm"] / 100
        for seg in segments
    )

    confidence_colors = {"high": "#27AE60", "medium": "#F39C12", "low": "#E74C3C"}
    conf = analysis.get("confidence", "medium")
    conf_color = confidence_colors.get(conf, "#888")
    conf_labels = {"high": "高", "medium": "中", "low": "低"}
    conf_label = conf_labels.get(conf, conf)

    shape_labels = {
        "rectangular": "矩形",
        "L-shaped": "L 形",
        "U-shaped": "U 形",
        "irregular": "不規則形",
    }
    shape_label = shape_labels.get(analysis.get("room_shape", ""), analysis.get("room_shape", ""))

    tile_source = "使用者提供" if analysis.get("tile_estimation_source") == "user_provided" else "AI 估算"

    info_text = (
        f"房間格局：{shape_label}　　"
        f"磁磚尺寸：{analysis['tile_width_cm']:.0f}×{analysis['tile_height_cm']:.0f} cm（{tile_source}）　　"
        f"估算面積：{total_area:.1f} m²　　"
        f"分析信心度：{conf_label}"
    )

    ax.set_title("房間格局俯視圖", fontsize=14, fontweight="bold", pad=16, color="#2C3E50")

    padding = margin * 0.6
    ax.set_xlim(min(all_x) - margin, max(all_x) + padding)
    ax.set_ylim(min(all_y) - margin, max(all_y) + padding)
    ax.set_xlabel("寬度 (m)", fontsize=10)
    ax.set_ylabel("長度 (m)", fontsize=10)

    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}"))
    ax.tick_params(labelsize=8)

    compass = ax.inset_axes([0.88, 0.88, 0.1, 0.1])
    compass.set_xlim(-1.5, 1.5)
    compass.set_ylim(-1.5, 1.5)
    compass.set_aspect("equal")
    compass.axis("off")
    compass.annotate("", xy=(0, 1.2), xytext=(0, 0),
                     arrowprops=dict(arrowstyle="-|>", color="#2C3E50", lw=2))
    compass.text(0, 1.4, "N", ha="center", va="bottom", fontsize=9, color="#2C3E50", fontweight="bold")

    fig.text(
        0.5, 0.01,
        info_text,
        ha="center", va="bottom",
        fontsize=8.5, color="#555",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#F8F9FA", edgecolor="#DDD"),
    )

    if analysis.get("analysis_notes"):
        fig.text(
            0.5, -0.04,
            f"備註：{analysis['analysis_notes'][:120]}{'...' if len(analysis.get('analysis_notes','')) > 120 else ''}",
            ha="center", va="bottom",
            fontsize=7.5, color="#888",
            wrap=True,
        )

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
