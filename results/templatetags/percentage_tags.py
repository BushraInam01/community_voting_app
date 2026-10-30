from django import template

register = template.Library()


@register.filter
def percentage_width(value):
    try:
        percentage = float(value)
    except (TypeError, ValueError):
        return 0

    return max(0, min(percentage, 100))
