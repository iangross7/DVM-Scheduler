import calendar
import copy
from typing import List, Dict, Optional, Tuple
from workday import WorkDay, DVM, DAY_TYPE

# Scheduler for veterinarian clinic
class Scheduler:
    """
    Builds a monthly schedule of WorkDay objects for DVMs with greedy initialization
    and hill-climbing optimization to meet target hours and constraints.

    Calendar uses 0=Monday..6=Sunday; only 0..5 (Mon..Sat) are scheduled.
    """
    def __init__(
        self,
        month: int,
        year: int,
        closedDict: Dict[int, str],  # map day-of-month to closure reason
        vacationArray: List[List[Tuple[int, int, int]]],  # per-DVM list of (day, start, end)
        satSurgeon: DVM,
        prevDays: Optional[List[WorkDay]] = None,
        satSurgeonDayOff: int = 0,  # which Saturday (1-4) surgeon takes off
    ):
        # Validate month
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid month: {month}")
        self.month = month
        self.year = year

        # First weekday and number of days
        self.firstWeekday, self.numDays = calendar.monthrange(year, month)

        # Compute padding for full Mon-Sat weeks
        self.monthStartOffset = self.firstWeekday if self.firstWeekday < 6 else 0
        lastWeekday = (self.firstWeekday + self.numDays - 1) % 7
        self.monthEndOffset = 0 if lastWeekday == 6 else max(0, 5 - lastWeekday)

        # Build schedule array
        self.schedule: List[WorkDay] = []
        
        # Prepend previous-month days if needed
        if self.monthStartOffset > 0:
            if prevDays is None or len(prevDays) != self.monthStartOffset:
                raise ValueError(
                    f"Incorrect prior days: expected {self.monthStartOffset}, got {len(prevDays) if prevDays else 0}"
                )
            self.schedule.extend(prevDays)

        # Current month days
        for day in range(1, self.numDays + 1):
            wkday = (self.firstWeekday + day - 1) % 7
            if wkday == 6:  # skip Sundays
                continue
            isOpen = day not in closedDict
            self.schedule.append(
                WorkDay(
                    weekday=wkday,
                    date=day,
                    month=month,
                    year=year,
                    isOpen=isOpen,
                    closedReason=closedDict.get(day, "")
                )
            )

        # Trailing next-month padding
        nextMonth = (month % 12) + 1
        nextYear = year + (1 if month == 12 else 0)
        for pad in range(1, self.monthEndOffset + 1):
            wkday = calendar.weekday(nextYear, nextMonth, pad)
            if wkday < 6:
                self.schedule.append(
                    WorkDay(weekday=wkday, date=pad, month=nextMonth, year=nextYear)
                )

        # Apply vacation requests
        for dvm in DVM:
            vacs = vacationArray[dvm.value] if dvm.value < len(vacationArray) else []
            for dayNum, start, end in vacs:
                idx = (dayNum - 1) + self.monthStartOffset
                if 0 <= idx < len(self.schedule):
                    self.schedule[idx].setVacation(dvm, start, end)

        # Saturday surgeon configuration
        self.satSurgeon = satSurgeon
        self.satSurgeonDayOff = satSurgeonDayOff
        # Track which Saturdays each DVM works (ordinals)
        self.saturdayRecord: Dict[int, List[int]] = {d.value: [] for d in DVM}

    def generateSchedule(self) -> None:
        """
        Build initial greedy schedule then refine via hill-climbing.
        """
        # Initialize hours tracking
        self.weeklyHours = {d.value: 0 for d in DVM}
        self.monthlyHours = {d.value: 0 for d in DVM}

        # Greedy pass: process week-by-week
        week: List[WorkDay] = []
        for day in self.schedule:
            if day.isOpen:
                week.append(day)
            if len(week) == 6:
                self.weeklyHours = {d.value: 0 for d in DVM}
                self._processWeek(week)
                week = []
        if week:
            self.weeklyHours = {d.value: 0 for d in DVM}
            self._processWeek(week)

        # Hill-climbing optimization
        self._hillClimb()

    def _processWeek(self, days: List[WorkDay]) -> None:
        for day in days:
            self._scheduleDay(day)

    def _scheduleDay(self, day: WorkDay) -> None:
        """
        Greedy assignment per day:
        1) LO/JA both
        2) LP Friday surgery
        3) Routine surgery with fallback
        4) Two appointments + optional third
        5) Stagger lunches
        6) Saturday slots (surgeon + 2 appts)
        """
        openHour = 8
        lastThroughHour = 19 if day.weekday < 2 else 17
        
        # --- LO fixed schedule (M: appt, T: BOTH, W/F: off, Th: appt) ---
        if day.weekday == 0:
            # Monday: LO full-day appointments
            if day.ableToSchedule(DVM.LO, openHour, lastThroughHour):
                day.setVet(DVM.LO, openHour, lastThroughHour, DAY_TYPE.APPOINTMENT)
                hrs = day.shifts[DVM.LO.value].workedHours
                self.weeklyHours[DVM.LO.value] += hrs
                self.monthlyHours[DVM.LO.value] += hrs
        elif day.weekday == 1:
            # Tuesday: LO surgery into appts (BOTH)
            if day.ableToSchedule(DVM.LO, openHour, lastThroughHour):
                day.setVet(DVM.LO, openHour, lastThroughHour, DAY_TYPE.BOTH)
                hrs = day.shifts[DVM.LO.value].workedHours
                self.weeklyHours[DVM.LO.value] += hrs
                self.monthlyHours[DVM.LO.value] += hrs
        elif day.weekday in (2, 4):
            # Wednesday and Friday: LO standard off
            return
        elif day.weekday == 3:
            # Thursday: LO full-day appointments
            if day.ableToSchedule(DVM.LO, openHour, lastThroughHour):
                day.setVet(DVM.LO, openHour, lastThroughHour, DAY_TYPE.APPOINTMENT)
                hrs = day.shifts[DVM.LO.value].workedHours
                self.weeklyHours[DVM.LO.value] += hrs
                self.monthlyHours[DVM.LO.value] += hrs

        # --- End LO fixed schedule ---

        def canAddToSchedule(dvm: DVM, start: int, end: int) -> bool:
            # Checking if standard off / on vacation hours
            if not day.ableToSchedule(dvm, start, end): return False
            
            # enforce weekly/monthly caps
            hours = end - start + 1 - day.getLunchLength(end)
            if self.weeklyHours[dvm.value] + hours > 40:
                return False
            return True

        # 1) JA SURGERY INTO APPOINTMENTS DAY
        if day.weekday == 0:
            if canAddToSchedule(DVM.JA, openHour, lastThroughHour):
                day.setVet(DVM.JA, openHour, lastThroughHour, DAY_TYPE.BOTH)
                hrs = day.shifts[DVM.JA.value].workedHours
                self.weeklyHours[DVM.JA.value] += hrs
                self.monthlyHours[DVM.JA.value] += hrs

        # 2) LP Friday surgery no lunch
        if day.weekday == 4:
            if canAddToSchedule(DVM.LP, openHour, openHour + 7):
                day.setVet(DVM.LP, openHour, openHour + 7, DAY_TYPE.SURGERY)
                day.shifts[DVM.LP.value].lunchStart = None
                hrs = day.shifts[DVM.LP.value].workedHours + 1 # handles workedHours due to skipped lunch
                self.weeklyHours[DVM.LP.value] += hrs
                self.monthlyHours[DVM.LP.value] += hrs

        # 3) Routine surgeon except Wed (2), exclude EDS
        if day.weekday != 2:
            primary = {0: DVM.JA, 1: DVM.LO, 3: DVM.EJS, 4: DVM.LP}.get(day.weekday)
            surgeon = None
            if primary and primary != DVM.EDS and canAddToSchedule(primary, openHour, openHour+5):
                surgeon = primary
            else:
                for cand in [DVM.LP, DVM.LO, DVM.EJS, DVM.JA]:
                    if cand != DVM.EDS and canAddToSchedule(cand, openHour, openHour+5):
                        surgeon = cand
                        break
            if surgeon:
                day.setVet(surgeon, openHour, openHour+5, DAY_TYPE.SURGERY)
                hrs = day.shifts[surgeon.value].workedHours
                self.weeklyHours[surgeon.value] += hrs
                self.monthlyHours[surgeon.value] += hrs

        # 4) Appointments: 2 min, 3 max
        needed = 2
        extra = 1
        # 6) Saturday logic
        if day.weekday == 5:
            prevSats = [d for d in self.schedule if d.weekday == 5 and d.date < day.date]
            ordinal = len(prevSats) + 1
            # assign monthly surgeon
            if ordinal != self.satSurgeonDayOff:
                if canAddToSchedule(self.satSurgeon, openHour, openHour+5):
                    day.setVet(self.satSurgeon, openHour, openHour+5, DAY_TYPE.SURGERY)
                    hrs = day.shifts[self.satSurgeon.value].workedHours
                    self.weeklyHours[self.satSurgeon.value] += hrs
                    self.monthlyHours[self.satSurgeon.value] += hrs
                    self.saturdayRecord[self.satSurgeon.value].append(ordinal)
            # fill 2 appointments
            for start, end in [(openHour, lastThroughHour), (openHour, openHour+6)]:
                if needed == 0:
                    break
                for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                    if day.isWorking(d) or d == self.satSurgeon:
                        continue
                    if canAddToSchedule(d, start, end):
                        day.setVet(d, start, end, DAY_TYPE.APPOINTMENT)
                        hrs = day.shifts[d.value].workedHours
                        self.weeklyHours[d.value] += hrs
                        self.monthlyHours[d.value] += hrs
                        self.saturdayRecord[d.value].append(ordinal)
                        needed -= 1
                if needed == 0:
                    break
        #7) Non-Saturday Logic
        else:
            for start, end in [(openHour, lastThroughHour), (openHour, openHour+6)]:
                for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                    if needed == 0:
                        break
                    if day.isWorking(d):
                        continue
                    if canAddToSchedule(d, start, end):
                        day.setVet(d, start, end, DAY_TYPE.APPOINTMENT)
                        hrs = day.shifts[d.value].workedHours
                        self.weeklyHours[d.value] += hrs
                        self.monthlyHours[d.value] += hrs
                        needed -= 1
                if needed == 0:
                    break
            for start, end in [(openHour, lastThroughHour), (openHour, openHour+6)]:
                if extra == 0:
                    break
                for d in sorted(DVM, key=lambda d: self.monthlyHours[d.value]):
                    if day.isWorking(d):
                        continue
                    if canAddToSchedule(d, start, end):
                        day.setVet(d, start, end, DAY_TYPE.APPOINTMENT)
                        hrs = day.shifts[d.value].workedHours
                        self.weeklyHours[d.value] += hrs
                        self.monthlyHours[d.value] += hrs
                        extra -= 1
                if extra == 0:
                    break
        
        # Fallback assurance for numAppts on a given shift >= 2
        if day.getNumApptsOnShift() < 2:
            for d in sorted(DVM, key=lambda dv: self.monthlyHours[dv.value]):
                if day.getNumApptsOnShift() >= 2:
                    break
                if not day.isWorking(d) and canAddToSchedule(d, openHour, lastThroughHour):
                    day.setVet(d, openHour, lastThroughHour, DAY_TYPE.APPOINTMENT)
                    hrs = day.shifts[d.value].workedHours
                    self.weeklyHours[d.value] += hrs
                    self.monthlyHours[d.value] += hrs
        
        # 5) Stagger lunches
        self._staggerLunches(day)

    def _staggerLunches(self, day: WorkDay) -> None:
        """Assign lunch start times to avoid overlap."""
        windowStart = 12
        windowEnd = 14 if day.weekday < 2 else 13
        vets = [d for d in DVM if day.shifts[d.value].clockOut and day.shifts[d.value].clockOut > 14 and day.shifts[d.value].dayType != DAY_TYPE.SURGERY] # type: ignore
        order = sorted(vets, key=lambda d: (d != DVM.LP, self.monthlyHours[d.value]))
        for i, dvm in enumerate(order):
            start = windowStart + i
            if start >= windowEnd:
                start = windowStart
            day.shifts[dvm.value].lunchStart = start

    def _evaluate(self) -> float:
        """Objective: squared hour deviations + penalties."""
        score = 0.0
        # Hour targets
        targets = {DVM.LP.value: 125, DVM.EDS.value: 0}
        default = 170
        for dv in DVM:
            actual = self.monthlyHours[dv.value]
            tgt = targets.get(dv.value, default)
            score += (actual - tgt) ** 2
        # back-to-back Saturday
        satDates = {dv: [] for dv in DVM}
        for day in self.schedule:
            if day.weekday == 5:
                for dv in DVM:
                    if day.isWorking(dv):
                        satDates[dv].append(day.date)
        for dates in satDates.values():
            dates.sort()
            for i in range(1, len(dates)):
                if dates[i] - dates[i-1] == 7:
                    score += 100
        # half-day penalty
        for day in self.schedule:
            for dv in DVM:
                sh = day.shifts[dv.value]
                if sh.clockIn is not None and sh.clockOut is not None:
                    length = sh.clockOut - sh.clockIn + 1 
                    full = 8 if (day.weekday == 4 and sh.dayType == DAY_TYPE.SURGERY) else (12 if day.weekday < 2 else 10)
                    if length < full:
                        score += 10
        return score

    def _neighbors(self):
        """Yield neighbors by swapping two vets on the same day."""
        for idx, day in enumerate(self.schedule):
            if not day.isOpen:
                continue
            for i in range(len(DVM)):
                for j in range(i+1, len(DVM)):
                    d1, d2 = DVM(i), DVM(j)
                    if day.isWorking(d1) and day.isWorking(d2):
                        nb = copy.deepcopy(self)
                        nd = nb.schedule[idx]
                        s1, s2 = nd.shifts[i], nd.shifts[j]
                        # swap shift details
                        s1.clockIn, s2.clockIn = s2.clockIn, s1.clockIn
                        s1.clockOut, s2.clockOut = s2.clockOut, s1.clockOut
                        s1.dayType, s2.dayType = s2.dayType, s1.dayType
                        s1.lunchStart, s2.lunchStart = s2.lunchStart, s1.lunchStart
                        yield nb

    def _hillClimb(self) -> None:
        """Perform first-improvement hill-climbing."""
        current = self
        bestScore = current._evaluate()
        improved = True
        while improved:
            improved = False
            for nb in current._neighbors():
                nb._recalcHours()
                sc = nb._evaluate()
                if sc < bestScore:
                    current, bestScore = nb, sc
                    improved = True
                    break
        # adopt best
        self.schedule = current.schedule
        self.weeklyHours = current.weeklyHours
        self.monthlyHours = current.monthlyHours

    def _recalcHours(self) -> None:
        """Recompute weekly/monthly hours after neighbor move."""
        self.weeklyHours = {d.value: 0 for d in DVM}
        self.monthlyHours = {d.value: 0 for d in DVM}
        week: List[WorkDay] = []
        for day in self.schedule:
            if day.isOpen:
                week.append(day)
            if len(week) == 6:
                for wd in week:
                    for dv in DVM:
                        hrs = wd.shifts[dv.value].workedHours
                        self.weeklyHours[dv.value] += hrs
                        self.monthlyHours[dv.value] += hrs
                week = []
        if week:
            for wd in week:
                for dv in DVM:
                    hrs = wd.shifts[dv.value].workedHours
                    self.weeklyHours[dv.value] += hrs
                    self.monthlyHours[dv.value] += hrs

    def __str__(self) -> str:
        return "\n".join(str(d) for d in self.schedule)