from decimal import Decimal, InvalidOperation

from .errors import RuleViolation

ZERO = Decimal("0.00")


class Money:
    """Rupee amounts: exact decimals with at most two places, never floats."""

    MAX = Decimal("9999999.99")

    @classmethod
    def parse(cls, value, *, field: str, allow_zero: bool = False) -> Decimal:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise cls._invalid(field, "Enter a valid amount.")
        if not amount.is_finite():
            raise cls._invalid(field, "Enter a valid amount.")
        rounded = amount.quantize(ZERO)
        if rounded != amount:
            raise cls._invalid(field, "Use at most two decimal places.")
        if rounded < 0 or (rounded == 0 and not allow_zero):
            raise cls._invalid(field, "Enter an amount above zero." if not allow_zero
                               else "The amount cannot be negative.")
        if rounded > cls.MAX:
            raise cls._invalid(field, "This amount is too large.")
        return rounded

    @staticmethod
    def _invalid(field: str, message: str) -> RuleViolation:
        return RuleViolation(message, errors={field: [message]})


class Quantity:
    """Amounts of a thing, such as litres: above zero, at most two decimal places."""

    @classmethod
    def parse(cls, value, *, field: str, maximum: Decimal) -> Decimal:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise cls._invalid(field, "Enter a valid number.")
        if not amount.is_finite() or amount.quantize(ZERO) != amount:
            raise cls._invalid(field, "Use a number with at most two decimal places.")
        if amount <= 0 or amount > maximum:
            raise cls._invalid(field, f"Enter a number above zero, up to {maximum}.")
        return amount.quantize(ZERO)

    @staticmethod
    def _invalid(field: str, message: str) -> RuleViolation:
        return RuleViolation(message, errors={field: [message]})
