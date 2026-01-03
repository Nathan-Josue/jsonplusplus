import uuid
from datetime import datetime
# -----------------------------------------------------
#   TYPE DETECTION
# -----------------------------------------------------
INT_RANGES = [
    ("int8",   -128, 127),
    ("int16",  -32768, 32767),
    ("int32",  -2**31, 2**31 - 1),
    ("int64",  -2**63, 2**63 - 1),
]

UINT_RANGES = [
    ("uint8",  0, 255),
    ("uint16", 0, 65535),
    ("uint32", 0, 2**32 - 1),
    ("uint64", 0, 2**64 - 1),
]

def is_uuid(v):
    try:
        uuid.UUID(v)
        return True
    except:
        return False

def is_date(v):
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return True
    except:
        return False

def is_datetime(v):
    try:
        datetime.fromisoformat(v)
        return True
    except:
        return False

def detect_numeric_type_int(values):
    min_v = min(values)
    max_v = max(values)

    if min_v >= 0:
        for name, lo, hi in UINT_RANGES:
            if lo <= min_v and max_v <= hi:
                return name

    for name, lo, hi in INT_RANGES:
        if lo <= min_v and max_v <= hi:
            return name

    return "int64"

def detect_numeric_type_float(values):
    # IEEE 754
    F16_MIN, F16_MAX = -65504, 65504
    F32_MIN, F32_MAX = -3.4e38, 3.4e38

    fits_f16 = True
    fits_f32 = True

    for v in values:
        if not (F16_MIN <= v <= F16_MAX) or round(v, 3) != v:
            fits_f16 = False
        if not (F32_MIN <= v <= F32_MAX):
            fits_f32 = False

    if fits_f16:
        return "float16"
    if fits_f32:
        return "float32"
    return "float64"

def detect_type(values):
    # nullable<T>
    nullable = any(v is None for v in values)
    clean = [v for v in values if v is not None]

    if not clean:
        return "nullable<unknown>"

    first = clean[0]

    # bool
    if all(isinstance(v, bool) for v in clean):
        t = "bool"

    # int / uint
    elif all(isinstance(v, int) and not isinstance(v, bool) for v in clean):
        t = detect_numeric_type_int(clean)

    # float
    elif all(isinstance(v, float) for v in clean):
        t = detect_numeric_type_float(clean)

    # binary
    elif all(isinstance(v, (bytes, bytearray)) for v in clean):
        t = "binary"

    # string & dérivés
    elif all(isinstance(v, str) for v in clean):
        unique = set(clean)

        if all(is_uuid(v) for v in unique):
            t = "uuid"
        elif all(is_date(v) for v in unique):
            t = "date"
        elif all(is_datetime(v) for v in unique):
            t = "datetime"
        elif len(unique) <= 256:
            t = "enum"
        elif len(unique) <= len(clean) * 0.3:
            t = "string_dict"
        else:
            t = "string"

    # fallback
    else:
        t = "json"

    return f"nullable<{t}>" if nullable else t