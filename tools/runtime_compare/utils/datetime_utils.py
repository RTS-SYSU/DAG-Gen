"""Date time tool function"""

from datetime import datetime 


def now_ts_safe ()->str :
    """generate safe timestamp string (for File name)"""
    ts =datetime .now ().astimezone ().isoformat (timespec ="seconds")
    return ts .replace (":","-")
