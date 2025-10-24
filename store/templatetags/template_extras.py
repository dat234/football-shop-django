from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Cho phép truy cập dictionary item bằng key trong template"""
    return dictionary.get(key)