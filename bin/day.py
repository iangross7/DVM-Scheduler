'''
Class to represent a schedule day. 0 = Monday, 5 = Saturday.

@PARAMS
- dayNum (num 0-5 for day)
- isOpen (clinic open/closed)
- closedReason (description for clinic closed)

@DATAFIELDS:
- dayNum 
- isOpen
- closedReason
- clockIns (all below are same, 1x5 array for DVMs)
- clockOuts
- lunches
- aptTypes 
- vacationOff
- standardOff

Arrays Represent Order of DVMS being:
LO // LP // EJS // JA // EDS
'''
from lib.DVM import DVM

class Day:

    def __init__(self, dayNum, isOpen=True, closedReason=None):
        if dayNum < 0 or dayNum > 5:
            raise ValueError(f"Invalid Day of Week (got {dayNum})")

        self.dayNum = dayNum
        self.isOpen = isOpen # CLINIC CLOSED / HOLIDAYS
        if (not isOpen):
            self.closedReason = closedReason
            return

        self.clockIns = [None, None, None, None, None] # INT FOR HOUR IN
        self.clockOuts = [None, None, None, None, None] # INT FOR HOUR OUT
        self.lunches = [None, None, None, None, None] # INT FOR HOUR START

        self.aptTypes = [None, None, None, None, None]

        self.vacationOff = [False, False, False, False, False] # T/F FOR VACATION OFF

        if (dayNum == 0): # MONDAY OFFS (LP, EJS)
            self.standardOff = [False, True, True, False, False]
        elif (dayNum == 1): # TUESDAY OFFS (JA)
            self.standardOff = [False, False, False, True, False]
        if (dayNum == 2): # WEDNESDAY OFFS (LO, EDS)    
            self.standardOff = [True, False, False, False, True]
        elif (dayNum == 4): # FRIDAY OFFS  (LO)
            self.standardOff = [True, False, False, False, False]
        else: # NO AUTOMATIC OFFS FOR THURSDAY, SATURDAY
            self.standardOff = [False, False, False, False, False]

    def setVet(self, dvm: DVM, clockIn, clockOut, aptType, lunch=None):
        dvmIdx = dvm.value
        self.clockIns[dvmIdx] = clockIn
        self.clockOuts[dvmIdx] = clockOut
        self.aptTypes[dvmIdx] = aptType
        self.lunches[dvmIdx] = lunch

    def setVacation(self, dvm: DVM):
        self.vacationOff[dvm.value] = True
    
    # TODO: IMPLEMENT GET HOURS FUNCTION