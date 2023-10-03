from enum import IntEnum


class RecentDay(IntEnum):
    ONE = 1
    """近一日"""
    FIVE = 2
    """近五日"""
    TEN = 3
    """近十日"""
    TWENTY = 4
    """近二十日"""
    SIXTY = 5
    """近六十日"""
    ONE_HUNDRED_TWENTY = 6
    """近一百二十日"""
    TWO_HUNDRED_FORTY = 7
    """近二百四十日"""
