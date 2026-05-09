import anthropic
import base64
import json
import re
from pathlib import Path


ANALYSIS_PROMPT = """你是一位專業的室內空間分析師。請仔細觀察這張房間照片，分析地板磁磚的排列方式，估算房間的尺寸與格局。

使用者提供的磁磚尺寸: {tile_info}

請執行以下步驟：
1. 辨識照片中可見的地板磁磚
2. 計算各方向可見的磁磚數量（長度方向、寬度方向）
3. 根據透視角度補正，估算房間完整的磁磚數量
4. 推斷房間的形狀（矩形、L形、U形等）
5. 計算實際尺寸

請以 JSON 格式回傳分析結果，格式如下：
{{
  "tile_width_cm": <磁磚寬度（公分），若使用者有提供則使用提供的值>,
  "tile_height_cm": <磁磚高度（公分），若使用者有提供則使用提供的值>,
  "tile_estimation_source": "<'user_provided' 或 'ai_estimated'>",
  "tile_estimation_note": "<若為 AI 估算，說明依據；若為使用者提供則填 null>",
  "room_shape": "<'rectangular' | 'L-shaped' | 'U-shaped' | 'irregular'>",
  "segments": [
    {{
      "name": "<區域名稱，例如 '主要區域'、'延伸區域'>",
      "tiles_x": <X方向磁磚數量（整數）>,
      "tiles_y": <Y方向磁磚數量（整數）>,
      "offset_x": <相對於原點的X偏移磁磚數（整數，第一個區域填0）>,
      "offset_y": <相對於原點的Y偏移磁磚數（整數，第一個區域填0）>
    }}
  ],
  "confidence": "<'high' | 'medium' | 'low'>",
  "analysis_notes": "<分析說明，包含計算過程與可能的誤差來源>",
  "camera_angle": "<拍攝角度說明，例如 '站立視角，約45度俯角'>"
}}

重要：
- 所有數值必須是整數或浮點數，不要包含單位文字
- segments 陣列中的第一個元素代表主要區域，其 offset_x 和 offset_y 必須為 0
- 對於 L 形房間，使用兩個矩形段落描述
- 請盡可能精確，但誠實說明信心程度
"""


def encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def analyze_room(
    image_bytes: bytes,
    image_media_type: str,
    tile_width_cm: float | None = None,
    tile_height_cm: float | None = None,
    api_key: str | None = None,
) -> dict:
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    if tile_width_cm and tile_height_cm:
        tile_info = f"{tile_width_cm}cm × {tile_height_cm}cm（使用者提供）"
    else:
        tile_info = "未提供，請根據照片中的視覺線索自行估算常見磁磚尺寸（如 30×30、60×60、30×60 公分）"

    prompt = ANALYSIS_PROMPT.format(tile_info=tile_info)

    image_data = encode_image(image_bytes)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text

    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        raise ValueError(f"AI 回應中找不到 JSON 格式的資料。回應內容：\n{response_text}")

    result = json.loads(json_match.group())
    return result
