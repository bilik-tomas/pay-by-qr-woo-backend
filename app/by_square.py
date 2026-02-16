import base64
from io import BytesIO

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.image.svg import SvgImage

from pay_by_square import generate

from .schemas import PBSGenerateRequest


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
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

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


def payload_to_card_png_bytes(payload: str, qr_size: int = 460) -> bytes:
    qr_img = _resize_qr_nearest(_build_qr_image(payload, border=4, box_size=10), max(260, qr_size))
    qr_w, qr_h = qr_img.size

    pad_x = 42
    pad_y = 34
    title_h = 58
    subtitle_h = 30
    card_w = qr_w + (pad_x * 2)
    card_h = qr_h + (pad_y * 2) + title_h + subtitle_h

    # Card background.
    canvas = Image.new("RGB", (card_w, card_h), (245, 248, 255))
    draw = ImageDraw.Draw(canvas)

    # Rounded card.
    draw.rounded_rectangle(
        [4, 4, card_w - 5, card_h - 5],
        radius=26,
        fill=(255, 255, 255),
        outline=(203, 216, 241),
        width=2,
    )

    # Header texts.
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        sub_font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    title = "PAY by square"
    subtitle = "Naskenujte kod vo svojej bankovej aplikacii"
    title_box = draw.textbbox((0, 0), title, font=title_font)
    subtitle_box = draw.textbbox((0, 0), subtitle, font=sub_font)
    title_w = title_box[2] - title_box[0]
    subtitle_w = subtitle_box[2] - subtitle_box[0]
    draw.text(((card_w - title_w) // 2, 16), title, fill=(21, 47, 97), font=title_font)
    draw.text(((card_w - subtitle_w) // 2, 62), subtitle, fill=(84, 102, 140), font=sub_font)

    # QR zone.
    qr_x = (card_w - qr_w) // 2
    qr_y = title_h + subtitle_h + pad_y // 2
    draw.rounded_rectangle(
        [qr_x - 8, qr_y - 8, qr_x + qr_w + 8, qr_y + qr_h + 8],
        radius=16,
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
    style: str = "plain",
) -> bytes:
    style = (style or "plain").strip().lower()
    if style == "card":
        return payload_to_card_png_bytes(payload, qr_size=size)
    if framed:
        return base64.b64decode(payload_to_framed_png_base64(payload, label=label, qr_size=size))
    plain_qr = _resize_qr_nearest(_build_qr_image(payload, border=4, box_size=10), max(220, size))
    out = BytesIO()
    plain_qr.save(out, format="PNG")
    return out.getvalue()
