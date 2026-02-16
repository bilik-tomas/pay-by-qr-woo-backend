import base64
from io import BytesIO

import qrcode
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
