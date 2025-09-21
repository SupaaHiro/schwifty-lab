from langchain_core.tools import tool
from datetime import datetime


@tool
def get_today_date(format: str = "%Y-%m-%d") -> str:
    """
    Returns today's date in the specified format.

    Args:
      format (str): Date format according to the rules of datetime.strftime.
                    Default: "%Y-%m-%d".

    Returns:
      str: The date in the requested format.
    """

    today = datetime.now()

    if not format:
        format = "%Y-%m-%d"

    return today.strftime(format)


@tool
def get_current_time(format: str = "%H:%M:%S") -> str:
    """
    Returns the current time in the specified format.

    Args:
      format (str): Time format according to the rules of datetime.strftime. 
                    Default: "%H:%M:%S".

    Returns:
      str: The current time in the requested format.
    """
    now = datetime.now()

    if not format:
        format = "%H:%M:%S"

    return now.strftime(format)
