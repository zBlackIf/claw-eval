"""Function code enums and mutex group definitions."""
from enum import Enum


class FunctionCode(str, Enum):
    PAY_NO_PASSWORD = "PAY_NO_PASSWORD"
    DAILY_LIMIT = "DAILY_LIMIT"
    LIMIT_PER_TXN_5K = "LIMIT_PER_TXN_5K"
    AUTO_DEBIT = "AUTO_DEBIT"
    QUICK_PAY = "QUICK_PAY"
    BATCH_TRANSFER = "BATCH_TRANSFER"


# Mutual exclusion groups: codes within the same group cannot coexist
MUTEX_GROUPS = [
    [FunctionCode.PAY_NO_PASSWORD, FunctionCode.LIMIT_PER_TXN_5K],
    [FunctionCode.AUTO_DEBIT, FunctionCode.BATCH_TRANSFER],
    [FunctionCode.QUICK_PAY, FunctionCode.LIMIT_PER_TXN_5K, FunctionCode.BATCH_TRANSFER],
]
