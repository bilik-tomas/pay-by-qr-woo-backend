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


def payload_to_png_base64(payload: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    img.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def payload_to_framed_png_base64(payload: str, label: str = "PAY by square") -> str:
    # Keep QR quiet zone untouched; frame is only around the full QR image.
    qr = qrcode.QRCode(border=4, box_size=8)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

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
