from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Returns the value of a dictionary for a given key."""
    return dictionary.get(key)
