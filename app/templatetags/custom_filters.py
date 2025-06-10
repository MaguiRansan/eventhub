import math

from django import template

register = template.Library()

@register.filter
def ljust(value, arg):
    try:
        start = int(float(value))
        end = int(float(arg))
        
        if start <= end:
            return range(start, end + 1)
        return []
    except (ValueError, TypeError):
        return []

@register.filter
def sub(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0.0

@register.filter
def modulo(value, arg):
    try:
        if float(arg) == 0:
            return None
        return float(value) % float(arg)
    except (ValueError, TypeError):
        return None

@register.filter
def floor(value):
    try:
        return math.floor(float(value))
    except (ValueError, TypeError):
        return 0 