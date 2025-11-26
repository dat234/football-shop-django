from django import template

register = template.Library()

@register.filter(name='vnd')
def vnd(value):
    """
    Chuyển đổi số thành định dạng tiền tệ Việt Nam.
    Ví dụ: 200000 -> 200.000
    """
    try:
        value = int(value)
        # Định dạng chuẩn quốc tế (200,000) rồi đổi dấu phẩy thành dấu chấm
        return "{:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return value