import calendar
from typing import List, Dict, Optional, Tuple
from workday import WorkDay, DVM, DAY_TYPE

class Scheduler:
    """
    Builds a monthly schedule of WorkDay objects for DVMs.

    Calendar uses 0=Monday..6=Sunday; we only track 0..5 (Mon..Sat).

    IMPLICIT FIELDS:
    - schedule: List[WorkDay]; list of workdays including padding to fill full Mon-Sat weeks
    - numDays: int; total number of days in the month
    - firstWeekday: int; weekday index of the month's 1st (0=Mon..6=Sun)
    - monthStartOffset: int; number of WorkDay slots before the 1st to align with weekday
    - monthEndOffset: int; number of WorkDay slots after the last day to complete final week
    """
    def __init__(
        self,
        month: int,
        year: int,
        closedDict: Dict[int, str],  # day to reason of closure
        vacationArray: List[List[Tuple[int, int, int]]], # list of DVM's vacation requests, indexed by DVM
                                                         # tuple: day, clockIn, clockOut
        satSurgeon: DVM,  # sat surgeon of month
        prevDays: Optional[List[WorkDay]] = None,  # days leading to current month
        satSurgeonDayOff: int = 0,  # which saturday surgeon took off (1st-4th; 0 = none selected)
    ):
        # Validate month/year
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid month: {month}")
        self.month = month
        self.year = year

        # Determine the weekday of the 1st and total days
        self.firstWeekday, self.numDays = calendar.monthrange(year, month)

        # Leading padding: only Mon..Sat count; Sunday offset zero
        self.monthStartOffset = self.firstWeekday if self.firstWeekday < 6 else 0

        # Trailing padding: fill through Saturday of last week
        lastWeekday = (self.firstWeekday + self.numDays - 1) % 7
        self.monthEndOffset = 0 if lastWeekday == 6 else max(0, 5 - lastWeekday)

        # Build schedule with leading padding
        self.schedule: List[WorkDay] = []
        if self.monthStartOffset > 0:
            if prevDays is None or len(prevDays) != self.monthStartOffset:
                raise ValueError(
                    f"Incorrect amount of prior month days passed. Expected {self.monthStartOffset}, got {len(prevDays) if prevDays else 0}"
                )
            self.schedule.extend(prevDays)

        # Populate current month WorkDay entries (skip Sundays)
        for day in range(1, self.numDays + 1):
            wkday = (self.firstWeekday + day - 1) % 7
            if wkday == 6:
                continue
            if day in closedDict:
                # <-- Added date, monthName, year when instantiating WorkDay
                self.schedule.append(
                    WorkDay(
                        weekday=wkday,
                        date=day,
                        month=month,
                        year=self.year,
                        isOpen=False,
                        closedReason=closedDict[day]
                    )
                )
            else:
                self.schedule.append(
                    WorkDay(
                        weekday=wkday,
                        date=day,
                        month=month,
                        year=self.year
                    )
                )

        # Add trailing padding for next month days (skip Sundays)
        nextMonth = month + 1 if month < 12 else 1
        nextYear = year if month < 12 else year + 1
        for pad in range(1, self.monthEndOffset + 1):
            wkday = calendar.weekday(nextYear, nextMonth, pad)
            if wkday < 6:
                # Date for next month padding uses pad value
                self.schedule.append(
                    WorkDay(
                        weekday=wkday,
                        date=pad,
                        month=nextMonth,
                        year=nextYear
                    )
                )

        # Apply vacation days (1-based input)
        for dvm in DVM:
            vacRequests = vacationArray[dvm.value] if dvm.value < len(vacationArray) else []
            for dayNum, startHour, endHour in vacRequests:
                idx = (dayNum - 1) + self.monthStartOffset
                if 0 <= idx < len(self.schedule):
                    self.schedule[idx].setVacation(dvm, startHour, endHour)
                    
    #TODO: METHOD FOR THE SCHEDULING!!!

    def __str__(self) -> str:
        return "\n".join(str(day) for day in self.schedule)
