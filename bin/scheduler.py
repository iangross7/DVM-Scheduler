import calendar
from day import Day
from typing import List
from lib.DVM import DVM

class Scheduler:
    """
    Class used to schedule.

    Using Calendar module, days are zero-based indexed, months are one-based indexed.

    @PARAMS
    - month: INT of month
    - year: INT of year
    - closedDict: DICT where key = day closed, value = reason
    - vacationArray: LIST where each idx corresponds to DVM containing a list of their days off
                    [[1, 28], [], [], [3 4 5], []]
    - prevDays: LIST of DAY objects for days in previous month (ACTUAL DAY OBJECTS)
    - satSurgeon: which is the sat Surgeon of the month
    - satSurgeonDayOff: boolean which saturday the monthly sat surgeon requested off

    @DATAFIELDS
    - ALL PARAMS PLUS:
    - numDays: number of days in current month
    - firstDayOfMonth: which type of day for FOM (0-6)
    - lastDayOfMonth: which type of day for EOM (0-6)
    - monthStartOffset: how many days prior to month start (IDX ADD)
    - monthEndOffset: how many days after month end (IDX ADD)
    - schedule: array representation of the schedule. contains pre-month and post-month days for full weeks
    """

    NUM_DVMs = 5

    def __init__(self, month, year, closedDict, vacationArray, satSurgeon: DVM,
                 prevDays=None, satSurgeonDayOff=None):
        
        self.month = month
        self.year = year

        _, self.numDays = calendar.monthrange(year, month)

        self.firstDayOfMonth = calendar.weekday(year, month, 1) # OUTPUTTING ACTUAL DAY OBJECT NOT INT
        self.monthStartOffset = self.firstDayOfMonth % 6 # when current month starts in array

        # TODO: VACATION DAY INPUT/CALCULATORS FOR THIS
        self.lastDayOfMonth = calendar.weekday(year, month, self.firstDayOfMonth)
        if (self.lastDayOfMonth == 6):
            self.monthEndOffset = 0 # how many extra days in array to complete a week
        else:
            self.monthEndOffset = 5 - self.lastDayOfMonth

        self.schedule: List[Day] = [] # list of Mon-Sat Days. % 6 = 0 is Mondays, % 6 = 5 is Saturday

        # Instantiates prior-to-month-days in array (for a full week)
        if (self.monthStartOffset != 0):
            if (prevDays is None or len(prevDays) != self.monthStartOffset):
                raise ValueError("Error: Invalid Amount of Prior Days for Month")
            for day in prevDays:
                self.schedule.append(day)
        
        # Instantiates days actually in month in array
        for i in range(1, self.numDays + 1):
            dayOfWeek = calendar.weekday(year, month, i)
            if (dayOfWeek == 6): pass
            
            if i in closedDict:
                self.schedule.append(Day(dayOfWeek, False, closedDict[i]))
            else:
                self.schedule.append(Day(i))

        # Instantiates post-month-days in array (for a full week)
        for i in range (1, self.monthEndOffset + 1):
            tempYear = year
            tempMonth = month
            if month == 12: 
                tempYear = year +1
                tempMonth = 1

            dayOfWeek = calendar.weekday(tempYear, tempMonth, i)
            self.schedule.append(Day(i))

        # Implementing declared vacation days. i is DVM_IDX
        for i in range(Scheduler.NUM_DVMs):
            for j in vacationArray[i]:
                self.schedule[j + self.monthStartOffset].setVacation(i)
        
        #TODO: Implement fixed Days, Sat Surgeon Days, Sat Surgeon Days Off 