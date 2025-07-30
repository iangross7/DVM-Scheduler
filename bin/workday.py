from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import List, Optional, Tuple
import calendar

# DVM's name corresponding to their index
class DVM(IntEnum):
    LO = 0
    LP = 1
    EJS = 2
    JA = 3
    EDS = 4

# Types of day events
class DAY_TYPE(Enum):
    APPOINTMENT = "APPOINTMENT"
    SURGERY = "SURGERY"
    BOTH = "BOTH"

# Lunch durations by dayNum (0=Mon..5=Sat) (CLOSED SUN)
LUNCH_LENGTH = {0: 2, 1: 2, 2: 1, 3: 1, 4: 1, 5: 1}

# Standard off-days mapping by dayNum
STANDARD_OFF = {
    0: [DVM.LP, DVM.EJS],
    1: [DVM.JA],
    2: [DVM.LO, DVM.EDS],
    4: [DVM.LO],
}

@dataclass
class Shift:
    """
    Object representing a DVM's shift on a given day.
    """
    dayNum: int = 0  # day of week (0-5)
    clockIn: Optional[int] = None  # time in
    clockOut: Optional[int] = None  # MILITARY time worked through (exit hour + 1)
    lunchStart: Optional[int] = None  # start of lunch time
    dayType: Optional[DAY_TYPE] = None  # type of day event (appointment or surgery)
    vacation: Optional[Tuple[int, int]] = None  # (start hour, end hour) of vacation
    standardOff: bool = False  # whether or not a std day off

    @property
    def workedHoursAfterLunchSet(self) -> int:
        if self.clockIn is None or self.clockOut is None:
            return 0
        total = self.clockOut - self.clockIn + 1
        if self.lunchStart is not None:
            length = LUNCH_LENGTH.get(self.dayNum, 1)
            total -= length
        return total
    
    @property
    def workedHours(self) -> int:
        if self.clockIn is None or self.clockOut is None:
            return 0
        total = self.clockOut - self.clockIn + 1
        
        # Handles lunch hours even if not declared yet
        if self.clockOut > 13:
            lunchHours = 1 if self.dayNum > 1 else 2
            total -= lunchHours
            
        return total

@dataclass
class WorkDay:
    """
    Object representing an entire clinic workday.
    """
    weekday: int  # day of week (0-5)
    date: int # day of week (1-31)
    month: int # int of month (1-12)
    year: int # int of year; ex 2025
    isOpen: bool = True  # whether or not clinic itself is open
    closedReason: str = ""  # reason for closure
    shifts: List[Shift] = field(init=False)

    def __post_init__(self):
        if not (0 <= self.weekday <= 5):
            raise ValueError(f"Invalid weekday (0-5): {self.weekday}")

        self.shifts = [Shift(dayNum=self.weekday) for _ in DVM]

        for dvm in STANDARD_OFF.get(self.weekday, []):
            self.shifts[dvm.value].standardOff = True

    def setVet(self, dvm: DVM, clockIn: int, clockOut: int,
               dayType: Optional[DAY_TYPE], lunchStart: Optional[int] = None):
        """
        Schedule a DVM's shift. dayType must be DAY_TYPE or None.
        """
        if not (8 <= clockIn < 19 and 8 < clockOut <= 19 and clockIn < clockOut):
            raise ValueError(f"Invalid clock times: {clockIn}-{clockOut}")

        shift = self.shifts[dvm.value]

        if shift.standardOff:
            raise ValueError("Tried to schedule on a standard day off.")
        if shift.vacation:
            vacStart, vacEnd = shift.vacation
            if clockIn < vacEnd and clockOut > vacStart:
                raise ValueError(f"Shift overlaps vacation hours {vacStart}-{vacEnd}")

        if dayType is not None and not isinstance(dayType, DAY_TYPE):
            raise ValueError(f"dayType must be DAY_TYPE or None, got {dayType}")
        
        if dvm is DVM.EDS and dayType is DAY_TYPE.SURGERY:
            raise ValueError("Tried to assign EDS to surgery")
        
        if ((dvm is not DVM.JA) and (dvm is not DVM.LO)) and dayType is DAY_TYPE.BOTH:
            raise ValueError(f"Tried to schedule SURGERY into APPT day for {dvm}")

        shift.clockIn = clockIn
        shift.clockOut = clockOut
        shift.dayType = dayType
        shift.lunchStart = lunchStart

    def setVacation(self, dvm: DVM, startHour: int, endHour: int):
        """
        Mark a DVM as on vacation for this day (partial or full day).
        """
        if not (0 <= startHour < endHour <= 24):
            raise ValueError(f"Invalid vacation hours: {startHour}-{endHour}")
        
        self.shifts[dvm.value].vacation = (startHour, endHour)
        
    def ableToSchedule(self, dvm: DVM, clockIn: int, clockOut: int) -> bool:
        """
        Return True if a DVM could be added to schedule.
        """
        if not (8 <= clockIn < 19 and 8 < clockOut <= 19 and clockIn < clockOut):
            raise ValueError(f"Invalid clock times: {clockIn}-{clockOut}")
        
        shift = self.shifts[dvm.value]
        if shift.standardOff:
            return False
        if shift.vacation:
            vac_start, vac_end = shift.vacation
            # if desired shift overlaps any part of vacation, cannot schedule
            if clockIn < vac_end and clockOut > vac_start:
                return False
        return True

    def isWorking(self, dvm: DVM) -> bool:
        """
        Return True if DVM is scheduled to work.
        """
        return self.shifts[dvm.value].clockIn is not None
    
    def getLunchLength(self, clockOut: int) -> int:
        """
        Returns 0 if no lunch needed, 1 for W-S, 2 for M&T
        """
        if clockOut < 13: return 0
        else:
            lunchTime = 1 if self.weekday > 1 else 2
            return lunchTime
    
    def getNumApptsOnShift(self) -> int:
        """
        Retrieves number of appointments on a given shift.
        """
        return len([d for d in self.shifts if d.dayType is DAY_TYPE.APPOINTMENT])
    
    def getNumSurgeonsOnShift(self) -> int:
        """
        Retrieves number of surgeons on a given shift. Accounts for special BOTH days.
        """
        return len([d for d in self.shifts if d.dayType is DAY_TYPE.APPOINTMENT or d.dayType is DAY_TYPE.BOTH])
        

    def __str__(self) -> str:
        """
        CLI representation of the workday.
        """
        header = f"{calendar.day_name[self.weekday]} {self.month}/{self.date}/{self.year}"
        if not self.isOpen:
            return header + f" Closed: {self.closedReason}"
        lines = [header]
        for d in DVM:
            shift = self.shifts[d.value]
            if shift.standardOff:
                lines.append(f"{d.name}: Standard Off")
            elif not self.isWorking(d):
                if shift.vacation:
                    vacStart, vacEnd = shift.vacation
                    lines.append(f"{d.name}: Vacation {vacStart}-{vacEnd}")
                else:
                    lines.append(f"{d.name}: Not Scheduled")
            else:
                s = (f"{d.name}: {shift.workedHours}h "
                        f"({shift.clockIn}-{shift.clockOut})")
                if shift.lunchStart is not None:
                    end = shift.lunchStart + LUNCH_LENGTH.get(self.weekday, 1)
                    s += f", lunch {shift.lunchStart}-{end}"
                if shift.dayType:
                    s += f" - {shift.dayType.value.title()}"
                lines.append(s)
        return "\n".join(lines) + "\n"
