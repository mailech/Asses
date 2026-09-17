"""Money handling for the booking domain.

Every amount is a ``Decimal`` quantised to whole cents with banker-unfriendly
but invoice-friendly ROUND_HALF_UP -- the rounding a finance team expects to see
on a statement. Floats never appear: 0.1 + 0.2 is not a defensible line item.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

CENTS: Final = Decimal("0.01")
ZERO: Final = Decimal("0.00")


def money(amount: Decimal) -> Decimal:
    """Round ``amount`` to the nearest cent, half away from zero."""
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
