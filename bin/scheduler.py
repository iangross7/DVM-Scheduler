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

        # Saturday settings
        self.satSurgeon = satSurgeon
        self.satSurgeonDayOff = satSurgeonDayOff
        self.scheduleSaturdays: List[int] = []

    def generateSchedule(self) -> None:
        """Run greedy scheduling then hill-climber optimization."""
        # Track hours
        self.weeklyHours = {d.value: 0 for d in DVM}
        self.monthlyHours = {d.value: 0 for d in DVM}

        # Process weeks
        week: List[WorkDay] = []
        for day in self.schedule:
            if day.isOpen:
                week.append(day)
            if len(week) == 6:
                self._processWeek(week)
                week = []
        if week:
            self._processWeek(week)

        # TODO: hill-climber swaps

    def _processWeek(self, days: List[WorkDay]) -> None:
        for day in days:
            self._scheduleDay(day)

    def _scheduleDay(self, day: WorkDay) -> None:
        openHour = 8
        lastWork = 19 if day.weekday < 2 else 17

        # Helper to enforce weekly (40h) and monthly (170h) caps
        def canTake(dvm: DVM, start: int, end: int) -> bool:
            hours = end - start + 1
            # subtract lunch if assigned
            shift = day.shifts[dvm.value]
            if shift.lunchStart is not None and shift.dayType != DAY_TYPE.SURGERY:
                hours -= (2 if day.weekday < 2 else 1)
            if self.weeklyHours[dvm.value] + hours > 40:
                return False
            if self.monthlyHours[dvm.value] + hours > 170:
                return False
            return True

        # 1) LO/JA combined surgery+appointment (BOTH)
        if day.weekday == 0 and canTake(DVM.JA, openHour, lastWork) and day.ableToSchedule(DVM.JA, openHour, lastWork):
            day.setVet(DVM.JA, openHour, lastWork, DAY_TYPE.BOTH)
            hrs = day.shifts[DVM.JA.value].workedHours
            self.weeklyHours[DVM.JA.value] += hrs
            self.monthlyHours[DVM.JA.value] += hrs
        if day.weekday == 1 and canTake(DVM.LO, openHour, lastWork) and day.ableToSchedule(DVM.LO, openHour, lastWork):
            day.setVet(DVM.LO, openHour, lastWork, DAY_TYPE.BOTH)
            hrs = day.shifts[DVM.LO.value].workedHours
            self.weeklyHours[DVM.LO.value] += hrs
            self.monthlyHours[DVM.LO.value] += hrs

        # 2) LP Friday 8h surgery no lunch
        if day.weekday == 4 and canTake(DVM.LP, openHour, openHour+7) and day.ableToSchedule(DVM.LP, openHour, openHour+7):
            day.setVet(DVM.LP, openHour, openHour+7, DAY_TYPE.SURGERY)
            day.shifts[DVM.LP.value].lunchStart = None
            hrs = day.shifts[DVM.LP.value].workedHours
            self.weeklyHours[DVM.LP.value] += hrs
            self.monthlyHours[DVM.LP.value] += hrs

        # 3) Routine surgeon except Wed, exclude EDS, with fallback
        if day.weekday != 2:
            primary = {0: DVM.JA, 1: DVM.LO, 3: DVM.EJS, 4: DVM.LP}.get(day.weekday)
            surgeon = None
            if primary and primary != DVM.EDS and canTake(primary, openHour, openHour+5) and day.ableToSchedule(primary, openHour, openHour+5):
                surgeon = primary
            else:
                for cand in [DVM.LP, DVM.LO, DVM.EJS, DVM.JA]:
                    if cand != DVM.EDS and canTake(cand, openHour, openHour+5) and day.ableToSchedule(cand, openHour, openHour+5):
                        surgeon = cand
                        break
            if surgeon:
                day.setVet(surgeon, openHour, openHour+5, DAY_TYPE.SURGERY)
                hrs = day.shifts[surgeon.value].workedHours
                self.weeklyHours[surgeon.value] += hrs
                self.monthlyHours[surgeon.value] += hrs

        # 4) Appointments min 2, max 3 (full-day then half-day)
        needed = 2
        extra = 1
        for slot in [(openHour, lastWork), (openHour, openHour+6)]:
            for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                if needed == 0:
                    break
                if day.isWorking(d):
                    continue
                start, end = slot
                if canTake(d, start, end) and day.ableToSchedule(d, start, end):
                    day.setVet(d, start, end, DAY_TYPE.APPOINTMENT)
                    hrs = day.shifts[d.value].workedHours
                    self.weeklyHours[d.value] += hrs
                    self.monthlyHours[d.value] += hrs
                    needed -= 1
            if needed == 0:
                break
        # optional third appointment
        for slot in [(openHour, lastWork), (openHour, openHour+6)]:
            for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                if extra == 0:
                    break
                if day.isWorking(d):
                    continue
                start, end = slot
                if canTake(d, start, end) and day.ableToSchedule(d, start, end):
                    day.setVet(d, start, end, DAY_TYPE.APPOINTMENT)
                    hrs = day.shifts[d.value].workedHours
                    self.weeklyHours[d.value] += hrs
                    self.monthlyHours[d.value] += hrs
                    extra -= 1
            if extra == 0:
                break

        # 5) Stagger lunches
        self._staggerLunches(day)

        # 6) Saturday logic: schedule satSurgeon on 3 of 4 Saturdays
        if day.weekday == 5:
            # Determine this Saturday's ordinal (1-4)
            saturdaysSoFar = [d for d in self.schedule if d.weekday == 5 and d.date < day.date]
            ordinal = len(saturdaysSoFar) + 1
            # If this is not the designated day off
            if ordinal != self.satSurgeonDayOff:
                # Schedule the monthly surgeon slot
                if canTake(self.satSurgeon, openHour, openHour+5) and day.ableToSchedule(self.satSurgeon, openHour, openHour+5):
                    day.setVet(self.satSurgeon, openHour, openHour+5, DAY_TYPE.SURGERY)
                    hrs = day.shifts[self.satSurgeon.value].workedHours
                    self.weeklyHours[self.satSurgeon.value] += hrs
                    self.monthlyHours[self.satSurgeon.value] += hrs
                    self.scheduleSaturdays.append(day.date)
            # Fill two appointment slots for Sat
            needed = 2
            for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                if needed == 0:
                    break
                if day.isWorking(d) or d == self.satSurgeon:
                    continue
                if canTake(d, openHour, lastWork) and day.ableToSchedule(d, openHour, lastWork):
                    day.setVet(d, openHour, lastWork, DAY_TYPE.APPOINTMENT)
                    hrs = day.shifts[d.value].workedHours
                    self.weeklyHours[d.value] += hrs
                    self.monthlyHours[d.value] += hrs
                    needed -= 1

    def _staggerLunches(self, day: WorkDay) -> None:
        windowStart = 12
        windowEnd = 14 if day.weekday < 2 else 13
        vets = [d for d in DVM if day.shifts[d.value].clockOut and day.shifts[d.value].clockOut > 14 and day.shifts[d.value].dayType != DAY_TYPE.SURGERY] # type: ignore
        order = sorted(vets, key=lambda d: (d != DVM.LP, self.monthlyHours[d.value]))
        for i, dvm in enumerate(order):
            start = windowStart + i
            if start >= windowEnd:
                start = windowStart
            day.shifts[dvm.value].lunchStart = start

    def __str__(self) -> str:
        return "\n".join(str(d) for d in self.schedule)


