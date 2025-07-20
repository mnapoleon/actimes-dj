from django import template


register = template.Library()


@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return None


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    try:
        return dictionary[key]
    except (KeyError, TypeError):
        return None


@register.filter
def driver_color(index):
    """Get a distinct color for each driver based on index"""
    colors = [
        '#DB0E15',  # Red
        '#2563eb',  # Blue
        '#16a34a',  # Green
        '#dc2626',  # Red-600
        '#7c3aed',  # Purple
        '#ea580c',  # Orange
        '#0891b2',  # Cyan
        '#be185d',  # Pink
        '#059669',  # Emerald
        '#b45309',  # Amber
    ]
    try:
        index = int(index)
        return colors[index % len(colors)]
    except (ValueError, TypeError):
        return '#DB0E15'  # Default to red
