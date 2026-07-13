def safe_prompt_format(template: str, **fields: str) -> str:
    """Format prompt templates without failing on stray braces in field values."""
    try:
        return template.format(**fields)
    except (KeyError, ValueError, IndexError):
        result = template
        for name, value in fields.items():
            result = result.replace("{" + name + "}", value)
        return result
