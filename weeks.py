import calendar


def get_weeks_of_month(year, month):
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")

    return [
        [day if day != 0 else None for day in week]
        for week in calendar.monthcalendar(year, month)
    ]
