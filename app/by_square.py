import base64
from io import BytesIO

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.image.svg import SvgImage

from pay_by_square import generate

from .schemas import PBSGenerateRequest


def _load_font(candidates: list[str], size: int):
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_payload(data: PBSGenerateRequest) -> str:
    kwargs = {
        "amount": float(data.amount),
        "iban": data.iban,
        "swift": data.bic,
        "beneficiary_name": data.recipient_name,
        "variable_symbol": data.variable_symbol,
        "note": data.message,
        "currency": data.currency,
    }
    if data.due_date:
        kwargs["payment_due_date"] = data.due_date.strftime("%Y-%m-%d")

    try:
        return generate(**kwargs)
    except TypeError:
        # Compatibility fallback for older pay-by-square library versions.
        kwargs.pop("payment_due_date", None)
        try:
            return generate(**kwargs)
        except TypeError:
            kwargs.pop("beneficiary_name", None)
            return generate(**kwargs)


def payload_to_svg(payload: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(image_factory=SvgImage)
    output = BytesIO()
    img.save(output)
    return output.getvalue().decode("utf-8")


def _build_qr_image(payload: str, border: int = 4, box_size: int = 10) -> Image.Image:
    qr = qrcode.QRCode(border=border, box_size=box_size)
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _resize_qr_nearest(image: Image.Image, target_size: int) -> Image.Image:
    if target_size <= 0:
        return image
    if image.width == target_size and image.height == target_size:
        return image
    return image.resize((target_size, target_size), resample=Image.Resampling.NEAREST)


def payload_to_png_base64(payload: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    img.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def payload_to_framed_png_base64(payload: str, label: str = "PAY by square", qr_size: int = 420) -> str:
    # Keep QR quiet zone untouched; frame is only around the full QR image.
    qr_img = _resize_qr_nearest(_build_qr_image(payload, border=4, box_size=10), max(220, qr_size))

    qr_w, qr_h = qr_img.size
    pad = 16
    title_h = 44
    border = 2
    canvas_w = qr_w + (pad * 2)
    canvas_h = qr_h + (pad * 2) + title_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans.ttf",
        ],
        24,
    )

    text_bbox = draw.textbbox((0, 0), label, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = max(0, (canvas_w - text_w) // 2)
    text_y = max(0, (title_h - text_h) // 2)
    draw.text((text_x, text_y), label, fill=(31, 47, 79), font=font)

    frame_top = title_h
    draw.rectangle(
        [1, frame_top + 1, canvas_w - 2, canvas_h - 2],
        outline=(31, 47, 79),
        width=border,
    )
    canvas.paste(qr_img, (pad, frame_top + pad))

    output = BytesIO()
    canvas.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def payload_to_card_png_bytes(
    payload: str,
    qr_size: int = 420,
    text_size: int = 20,
    subtitle_text: str = "Naskenujte kod vo svojej bankovej aplikacii",
    brand_text: str = "PAY by square",
) -> bytes:
    # `qr_size` is treated as final output image size in px.
    output_size = max(220, min(900, int(qr_size)))
    qr_target = max(150, int(round(output_size * 0.62)))
    qr_img = _resize_qr_nearest(_build_qr_image(payload, border=4, box_size=10), qr_target)
    qr_w, qr_h = qr_img.size

    safe_text_size = max(12, min(42, int(text_size)))
    scale = safe_text_size / 20.0

    subtitle_top = max(10, int(round(output_size * 0.05)))
    subtitle_to_qr_gap = max(8, int(round(output_size * 0.03)))
    qr_to_brand_gap = max(8, int(round(output_size * 0.03)))
    brand_to_bottom_gap = max(10, int(round(output_size * 0.05)))
    card_w = output_size

    # Card background.
    brand_font = _load_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ],
        max(14, int(round((safe_text_size + 16) * (output_size / 420.0)))),
    )
    sub_font = _load_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans.ttf",
        ],
        max(10, int(round(safe_text_size * (output_size / 420.0)))),
    )

    # Probe text sizes to compute dynamic header height.
    probe = Image.new("RGB", (1, 1), (255, 255, 255))
    probe_draw = ImageDraw.Draw(probe)
    subtitle = (subtitle_text or "").strip() or "Naskenujte kod vo svojej bankovej aplikacii"
    brand = (brand_text or "").strip() or "PAY by square"
    title_box = probe_draw.textbbox((0, 0), brand, font=brand_font)
    subtitle_box = probe_draw.textbbox((0, 0), subtitle, font=sub_font)
    title_w = title_box[2] - title_box[0]
    title_h = title_box[3] - title_box[1]
    subtitle_w = subtitle_box[2] - subtitle_box[0]
    subtitle_h = subtitle_box[3] - subtitle_box[1]

    qr_y = subtitle_top + subtitle_h + subtitle_to_qr_gap
    brand_y = qr_y + qr_h + qr_to_brand_gap
    card_h = max(output_size, brand_y + title_h + brand_to_bottom_gap)

    canvas = Image.new("RGB", (card_w, card_h), (245, 248, 255))
    draw = ImageDraw.Draw(canvas)

    # Rounded card.
    draw.rounded_rectangle(
        [4, 4, card_w - 5, card_h - 5],
        radius=max(16, int(round(26 * scale))),
        fill=(255, 255, 255),
        outline=(203, 216, 241),
        width=2,
    )

    draw.text(
        ((card_w - subtitle_w) // 2, subtitle_top),
        subtitle,
        fill=(84, 102, 140),
        font=sub_font,
    )
    draw.text(((card_w - title_w) // 2, brand_y), brand, fill=(21, 47, 97), font=brand_font)

    # QR zone.
    qr_x = (card_w - qr_w) // 2
    qr_border = max(5, int(round(output_size * 0.02)))
    qr_radius = max(10, int(round(output_size * 0.04)))
    draw.rounded_rectangle(
        [qr_x - qr_border, qr_y - qr_border, qr_x + qr_w + qr_border, qr_y + qr_h + qr_border],
        radius=qr_radius,
        fill=(255, 255, 255),
        outline=(226, 233, 247),
        width=2,
    )
    canvas.paste(qr_img, (qr_x, qr_y))

    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def payload_to_png_bytes(
    payload: str,
    framed: bool = False,
    label: str = "PAY by square",
    size: int = 420,
    text_size: int = 20,
    style: str = "plain",
    subtitle_text: str = "Naskenujte kod vo svojej bankovej aplikacii",
    brand_text: str = "PAY by square",
) -> bytes:
    style = (style or "plain").strip().lower()
    if style == "card":
        return payload_to_card_png_bytes(
            payload,
            qr_size=size,
            text_size=text_size,
            subtitle_text=subtitle_text,
            brand_text=brand_text,
        )
    if framed:
        return base64.b64decode(payload_to_framed_png_base64(payload, label=label, qr_size=size))
    plain_qr = _resize_qr_nearest(_build_qr_image(payload, border=4, box_size=10), max(220, size))
    out = BytesIO()
    plain_qr.save(out, format="PNG")
    return out.getvalue()
