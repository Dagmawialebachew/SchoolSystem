from django import template

register = template.Library()

@register.simple_tag
def get_fee(fees_dict, div_id, fee_type):
    """
    Retrieve a fee object from a dict using (div_id, fee_type) as key.
    """
    return fees_dict.get((div_id, fee_type))
