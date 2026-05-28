"""Function code enum + mutual-exclusion map."""
from enum import Enum


class FunctionCode(str, Enum):
    PAY_NO_PASSWORD = "PAY_NO_PASSWORD"          # 免密支付
    DAILY_LIMIT = "DAILY_LIMIT"                  # 每日限额
    LIMIT_PER_TXN_5K = "LIMIT_PER_TXN_5K"        # 单笔限额 5000
    FACE_RECOGNITION = "FACE_RECOGNITION"        # 人脸识别
    SMS_2FA = "SMS_2FA"                          # 短信双因子


# Sets of function codes that cannot co-exist.
MUTEX_GROUPS = [
    {"PAY_NO_PASSWORD", "LIMIT_PER_TXN_5K"},
    {"FACE_RECOGNITION", "SMS_2FA"},
]
