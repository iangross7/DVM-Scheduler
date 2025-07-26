from lib.DVM import DVM

class Day:
    """
    Class to represent a schedule day. 0 = Monday, 5 = Saturday.
    Clock In/Out/Lunch times are military time (24:00).

    @PARAMS
    - dayNum (num 0-5 for day)
    - isOpen (clinic open/closed)
    - closedReason (description for clinic closed)

    @DATAFIELDS:
    - dayNum 
    - isOpen
    - closedReason
    - clockIns (all below are same, 1xX array for DVMs)
    - clockOuts
    - lunches
    - aptTypes 
    - vacationOff
    - standardOff

    Arrays Follow DVM index set in DVM.py.
    """

    def __init__(self, dayNum:int, isOpen=True, closedReason:str=None):
        if dayNum < 0 or dayNum > 5:
            raise ValueError(f"Invalid Day of Week (got {dayNum})")
        
        numDvms = len(DVM)

        self.dayNum = dayNum
        self.isOpen = isOpen # CLINIC CLOSED / HOLIDAYS
        if (not isOpen):
            self.closedReason = closedReason
            return

        self.clockIns = [0] * numDvms # INT FOR HOUR IN (MILITARY TIME)
        self.clockOuts = [0] * numDvms # INT FOR HOUR OUT (WORKED THROUGH)
        self.lunches = [0] * numDvms # INT FOR HOUR START 

        self.aptTypes = [None] * numDvms

        self.vacationOff = [False] * numDvms # T/F FOR VACATION OFF

        self.standardOff = [False] * numDvms # T/F FOR STANDARD DAY OFGF

        if (dayNum == 0): # MONDAY OFFS (LP, EJS)
            self.standardOff[DVM.LP.value] = True
            self.standardOff[DVM.EJS.value] = True
        elif (dayNum == 1): # TUESDAY OFFS (JA)
            self.standardOff[DVM.JA.value] = True
        elif (dayNum == 2): # WEDNESDAY OFFS (LO, EDS)
            self.standardOff[DVM.LO.value] = True
            self.standardOff[DVM.EDS.value] = True    
        elif (dayNum == 4): # FRIDAY OFFS  (LO)
            self.standardOff[DVM.LO.value] = True
        # NO AUTOMATIC OFFS FOR THURSDAY, SATURDAY
    
    def __str__(self):
        retStr = ""
        for dvm in DVM:
            hours = self.getHoursWorked(dvm)
            if (hours == 0): retStr += dvm.name + ": OFF TODAY."
            else:
                clockIn, clockOut = self.getClockHours(dvm)
                retStr += dvm.name + ": " + str(hours) + " hours //// " + str(clockIn) + "-" + str(clockOut)
                lunchHours = self.getLunchHours(dvm)
                if (lunchHours):
                    retStr += "; lunch from " + str(lunchHours[0]) + "-" + str(lunchHours[1])
            retStr += "\n"
        return retStr

    def setVet(self, dvm: DVM, clockIn, clockOut, aptType, lunch=None):
        dvmIdx = dvm.value
        self.clockIns[dvmIdx] = clockIn
        self.clockOuts[dvmIdx] = clockOut
        self.aptTypes[dvmIdx] = aptType
        self.lunches[dvmIdx] = lunch

    def setVacation(self, dvm: DVM):
        self.vacationOff[dvm.value] = True
    
    def isWorking(self, dvm: DVM):
        return self.clockIns[dvm.value] > 0
    
    def getClockHours(self, dvm: DVM):
        if (self.isWorking(dvm)): return self.clockIns[dvm], self.clockOuts[dvm]
        else: return None
    
    def getLunchHours(self, dvm: DVM):
        lunchStart = self.lunches[dvm.value]
        if (lunchStart == 0): return None
        else:
            if (self.dayNum <= 1):
                return lunchStart, lunchStart + 2
            else:
                return lunchStart, lunchStart + 1

    def getHoursWorked(self, dvm: DVM):
        """
        Returns how many hours a DVM worked, accounting for lunch breaks.
        Time is in military. Clock out is the hour they work through:
        (19 = 7PM means clocked out at 8PM)
        """
        dvmIdx = dvm.value
        if (not self.isWorking(dvm)): return 0

        clockDiff = self.clockOuts[dvmIdx] - self.clockIns[dvmIdx] + 1

        if (self.lunches[dvmIdx] == 0):
            return clockDiff
        else:
            if (self.dayNum <= 1):
                return (clockDiff - 2)
            else:
                return (clockDiff - 1)