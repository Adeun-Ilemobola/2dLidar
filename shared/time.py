
import time

from typing import Optional

class Timer:
    def __init__(self , set_time: Optional[float] = None , tick_rate : float = 0.1 , ):
        self.start_time = time()

        self.run :bool = False

        self.sim_time : float = 0.0
        self.max_sime_time : Optional[float] = set_time
        self.clock_tick : float =  time .perf_counter() + 0.020 
        self.tick_rate : float = tick_rate



        self.start()

    def start(self):
        if self.sim_time  in (0.0 , None):
            return
        now = time.perf_counter()

        if now  >= self.clock_tick:
            self.sim_time  +=self.tick_rate
            self.clock_tick  +=  0.020

            if self.sim_time  >= self.max_sime_time :
                self.run  = True

    def reset(self):
        self.sim_time = 0.0
        self.clock_tick = time.perf_counter() + 0.020
        self.run = False