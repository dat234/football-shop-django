from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Nhân value với arg"""
    try:
        return value * arg
    except (ValueError, TypeError):
        return ''