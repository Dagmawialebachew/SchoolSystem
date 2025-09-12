# app/templatetags/form_extras.py
from django import template

register = template.Library()

@register.inclusion_tag("partials/form_field.html")
def render_field(field):
    return {"field": field}
