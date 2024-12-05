import calendar

def get_weeks_of_month(year, month):
    matrix = calendar.monthcalendar(year,month)

    weeks = []
    for week in matrix:
        tyden = []
        for day in week:
            den = 0
            if day == 0:
                den = None
            else:
                den = day
            tyden.append(den)
        weeks.append(tyden)

    return weeks

weeks_november_2023 = get_weeks_of_month(2023, 11)

for week in weeks_november_2023:
    print(week)