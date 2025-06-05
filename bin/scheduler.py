'''
Class used to schedule.

Using Calendar module, days are zero-based indexed, months are one-based indexed.
'''
import calendar
from day import Day
from typing import List

'''
closedDict: dict where key = day closed, value = reason
vacationArray: array where each idx corresponds to DVM containing a list of their days off
self.schedule: array representation of the schedule. contains pre-month and post-month days for full weeks.
'''
NUM_DVMs = 5

class Scheduler:
    def __init__(self, month, year, closedDict, vacationArray, 
                 prevDays=None, satSurgeonDayOff=None, satSurgeon=None):
        
        _, self.numDays = calendar.monthrange(year, month)

        self.firstDayOfMonth = calendar.weekday(year, month, 1)
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
            self.schedule.append(Day(i))

        # Implementing declared vacation days. i is DVM_IDX
        for i in range(NUM_DVMs):
            for j in vacationArray[i]:
                self.schedule[j + self.monthStartOffset].setVacation(i)
        
        #TODO: Implement fixed Days, Sat Surgeon Days, Sat Surgeon Days Off 