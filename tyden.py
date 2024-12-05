import calendar

class Tyden:
    def __init__(self,rok, mesic):
        self.rok = rok
        self.mesic = mesic

    def ziskatMatici(self):
        matrix = calendar.monthcalendar(self.rok, self.mesic)

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

