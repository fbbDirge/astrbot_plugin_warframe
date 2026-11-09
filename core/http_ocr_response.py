"""Extract verbatim OCR text from standalone HTTP OCR responses."""


def response_text(payload: object) -> str:
    """Prefer plain text, then text, then ordered words_result; never merge duplicates.

    Numeric artifacts remain untouched for the downstream riven validation step.
    """
    if not isinstance(payload, dict):
        raise ValueError('OCR 接口必须返回 JSON 对象')
    for key in ('plain_text', 'text'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    rows = payload.get('words_result')
    if isinstance(rows, list):
        lines = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('words'), str):
                raise ValueError('OCR words_result 格式不正确')
            if row['words'].strip():
                lines.append(row['words'].strip())
        if lines:
            return '\n'.join(lines)
    raise ValueError('OCR 接口未返回可识别的文字')
