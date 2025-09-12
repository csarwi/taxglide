from decimal import Decimal
from .models import round_to_increment

def final_round(amount: Decimal, inc: int) -> Decimal:
    return round_to_increment(amount, inc) if inc else amount