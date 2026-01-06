"""
Date formatting utilities for backend
"""
from datetime import datetime, date
from typing import Optional, Union


def format_date(
    date_obj: Optional[Union[datetime, date, str]],
    date_format: str = "DD/MM/YYYY",
    language: str = "en"
) -> str:
    """
    Format a date according to user preference
    
    Args:
        date_obj: Date object, datetime object, or ISO string
        date_format: Date format preference (DD/MM/YYYY, DD/Month/YYYY, MM/DD/YYYY, or DD/MM/YY)
        language: Language code for month names (en or ro)
    
    Returns:
        Formatted date string
    """
    if not date_obj:
        return ""
    
    try:
        # Convert to datetime if needed
        if isinstance(date_obj, str):
            # Try to parse ISO format string
            if 'T' in date_obj:
                dt = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_obj)
        elif isinstance(date_obj, date) and not isinstance(date_obj, datetime):
            dt = datetime.combine(date_obj, datetime.min.time())
        else:
            dt = date_obj
        
        day = str(dt.day).zfill(2)
        month = dt.month
        month_str = str(month).zfill(2)
        year = dt.year
        year_short = str(year)[2:]
        
        if date_format == "DD/Month/YYYY":
            month_names = {
                "en": [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ],
                "ro": [
                    "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
                    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"
                ]
            }
            month_name = month_names.get(language, month_names["en"])[month - 1]
            return f"{day}/{month_name}/{year}"
        elif date_format == "MM/DD/YYYY":
            # American format
            return f"{month_str}/{day}/{year}"
        elif date_format == "DD/MM/YY":
            # Short year format
            return f"{day}/{month_str}/{year_short}"
        
        # Default DD/MM/YYYY format
        return f"{day}/{month_str}/{year}"
    
    except Exception as e:
        print(f"[format_date] Error formatting date: {e}")
        return ""


def format_date_with_preferences(
    date_obj: Optional[Union[datetime, date, str]],
    date_format: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """
    Format a date for display using user preferences
    
    Args:
        date_obj: Date to format
        date_format: Date format preference from user settings
        language: Language code from user settings
    
    Returns:
        Formatted date string
    """
    return format_date(
        date_obj,
        date_format or "DD/MM/YYYY",
        language or "en"
    )

