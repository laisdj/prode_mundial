from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(int(key))
    except (ValueError, TypeError):
        return None

@register.filter
def split(value, delimiter):
    return value.split(delimiter)