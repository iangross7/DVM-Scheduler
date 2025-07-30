from scheduler import Scheduler
from workday import WorkDay, DVM, DAY_TYPE
import calendar


testSched = Scheduler(6, 2025, {}, [[],[],[],[],[]], DVM.EJS)
testSched.generateSchedule()
print(testSched)

# testDay = WorkDay(0, 2, 6, 2025)
# testDay.setVet(DVM.JA, 8, 19, DAY_TYPE.BOTH)
# print(testDay.shifts[DVM.JA.value])

# day = calendar.weekday(2025, 6, 1)
# print(day + 1)