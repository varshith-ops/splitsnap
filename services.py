import json
import re
import smtplib
from email.mime.text import MIMEText

from google import genai
from google.genai import types

import prompts


def _to_float(value):
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def parse_receipt(api_key, model, image_bytes, mime_type):
    """Send a receipt photo to Gemini and return a cleaned dict."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompts.PARSE_REQUEST_PROMPT,
        ],
        config=types.GenerateContentConfig(
            system_instruction=prompts.SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    text = re.sub(r"```(?:json)?", "", response.text or "").strip()
    data = json.loads(text)

    items = []
    for row in data.get("items", []):
        name = str(row.get("item", "")).strip()
        price = _to_float(row.get("price"))
        if name and price > 0:
            items.append({"item": name, "price": price})

    return {
        "is_receipt": bool(data.get("is_receipt", True)) and bool(items),
        "items": items,
        "tax": _to_float(data.get("tax")),
        "tip": _to_float(data.get("tip")),
    }


def calculate_split(items, friends, tax, tip):
    """Per-person totals. Unassigned items are shared equally;
    tax and tip are shared in proportion to each person's food total."""
    n = len(friends)
    base = {f: 0.0 for f in friends}
    unassigned = 0.0
    for it in items:
        people = [p for p in it.get("assigned_to", []) if p in base]
        if people:
            for p in people:
                base[p] += it["price"] / len(people)
        else:
            unassigned += it["price"]
    for f in base:
        base[f] += unassigned / n

    subtotal = sum(base.values())
    extra = tax + tip
    return {
        f: base[f] + extra * (base[f] / subtotal if subtotal > 0 else 1 / n)
        for f in friends
    }


def send_email(sender, app_password, to_address, subject, body):
    try:
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to_address
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.send_message(message)
        return True, "sent"
    except Exception as error:
        return False, str(error)