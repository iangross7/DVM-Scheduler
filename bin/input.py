from scheduler import Scheduler
from day import Day
import calendar
from lib.DVM import DVM


testSched = Scheduler(6, 2025, {}, [[],[],[],[],[]], DVM.LP)
print(testSched)

# day = calendar.weekday(2025, 6, 1)
# print(day + 1)