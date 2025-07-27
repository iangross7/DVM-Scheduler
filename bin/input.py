from scheduler import Scheduler
from workday import WorkDay, DVM
import calendar


testSched = Scheduler(11, 2025, {}, [[],[],[],[],[]], DVM.LP)
print(testSched)

# day = calendar.weekday(2025, 6, 1)
# print(day + 1)