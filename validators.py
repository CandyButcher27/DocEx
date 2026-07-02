import re
from datetime import datetime

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")
MOBILE_RE = re.compile(r"^[6-9][0-9]{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ABHA_RE = re.compile(r"^[0-9]{14}$")
DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y")


def _pan(v):
    v = v.upper().replace(" ", "")
    return (v, "PAN format") if PAN_RE.match(v) else (None, "PAN format")


def _ifsc(v):
    v = v.upper().replace(" ", "")
    return (v, "IFSC format") if IFSC_RE.match(v) else (None, "IFSC format")


def _pin(v):
    v = re.sub(r"\s", "", v)
    return (v, "6-digit PIN") if PIN_RE.match(v) else (None, "6-digit PIN")


def _mobile(v):
    d = re.sub(r"\D", "", v)
    if len(d) > 10:
        d = d[-10:]
    return (d, "10-digit mobile") if MOBILE_RE.match(d) else (None, "10-digit mobile")


def _email(v):
    v = v.strip()
    return (v, "email format") if EMAIL_RE.match(v) else (None, "email format")


def _abha(v):
    d = re.sub(r"\D", "", v)
    return (d, "14-digit ABHA") if ABHA_RE.match(d) else (None, "14-digit ABHA")


def _date(v):
    v = v.strip()
    for fmt in DATE_FORMATS:
        try:
            return (datetime.strptime(v, fmt).strftime("%d-%m-%Y"), "date")
        except ValueError:
            continue
    return (None, "date")


def _amount(v):
    c = re.sub(r"[,\s₹rsRS.]", "", v) if not re.search(r"\.\d", v) else re.sub(r"[,\s₹]", "", v)
    c = c.strip()
    return (c, "numeric amount") if re.fullmatch(r"\d+(\.\d+)?", c) else (None, "numeric amount")


def _digits(v):
    d = re.sub(r"\s", "", v)
    return (d, "digits") if re.fullmatch(r"\d{5,}", d) else (None, "digits")


def _percent(v):
    d = re.sub(r"[%\s]", "", v)
    if re.fullmatch(r"\d{1,3}", d) and 0 <= int(d) <= 100:
        return (d, "0-100")
    return (None, "0-100")


_VALIDATORS = {
    "pan": _pan, "ifsc": _ifsc, "pin": _pin, "mobile": _mobile,
    "email": _email, "abha": _abha, "date": _date, "amount": _amount,
    "digits": _digits, "percent": _percent,
}


def _resolve(path):
    leaf = path.split(".")[-1]
    leaf = re.sub(r"\[\d+\]", "", leaf)
    if leaf == "pan_number":
        return "pan"
    if "ifsc" in leaf:
        return "ifsc"
    if leaf in ("pin", "pin_code"):
        return "pin"
    if "mobile" in leaf:
        return "mobile"
    if "email" in leaf:
        return "email"
    if "abha" in leaf:
        return "abha"
    if "percentage_share" in leaf:
        return "percent"
    if leaf in ("dob", "appointee_dob") or "date_of_birth" in leaf or leaf.endswith("_date"):
        return "date"
    if "income" in leaf or leaf == "loanAmount" or "premium" in leaf:
        return "amount"
    if "account_number" in leaf:
        return "digits"
    return None


def validate(path, value):
    name = _resolve(path)
    if name is None:
        return True, value, None
    ok_value, label = _VALIDATORS[name](value)
    if ok_value is None:
        return False, value, label
    return True, ok_value, label
