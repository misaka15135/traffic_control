import threading
import time
import random
import queue
from models import Vehicle

ew_green = True
light_lock = threading.Lock() 

# 队列：按序排队的车辆，每个方向有两个队列：普通车和特权车
queues = {
    "东": {"ordinary": queue.Queue(), "special": queue.Queue()},
    "西": {"ordinary": queue.Queue(), "special": queue.Queue()},
    "南": {"ordinary": queue.Queue(), "special": queue.Queue()},
    "北": {"ordinary": queue.Queue(), "special": queue.Queue()}
}

# 正在十字路口中心行驶的车辆（UI 动画读取此列表）
active_vehicles = []
log_messages = []

def add_log(msg):
    print(msg)
    log_messages.append(msg)
    if len(log_messages) > 15:
        log_messages.pop(0)

class ControllerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.init_vehicles()
        self.vehicle_generator = VehicleGeneratorThread()
        self.vehicle_generator.start()

    def init_vehicles(self):
        directions = ["东", "西", "南", "北"]
        special_types = ["消防车", "救护车", "警车"]
        for d in directions:
            for _ in range(4): # 初始每条路排4辆车
                v_type = "普通车"
                if random.random() < 0.3: 
                    v_type = random.choice(special_types)
                vehicle = Vehicle(random.randint(1, 100), d, v_type)
                if vehicle.is_special:
                    queues[d]["special"].put(vehicle)
                else:
                    queues[d]["ordinary"].put(vehicle)

    def run(self):
        global ew_green
        while True:
            state_str = "东西[绿] 南北[红]" if ew_green else "东西[红] 南北[绿]"
            add_log(f"【信号切换】8秒倒计时开始 -> {state_str}")
            time.sleep(8) 
            with light_lock:
                ew_green = not ew_green

class VehicleGeneratorThread(threading.Thread):
    def __init__(self, min_interval=0.2, max_interval=1.5):
        super().__init__(daemon=True)
        self.min_interval = min_interval
        self.max_interval = max_interval

    def run(self):
        while True:
            time.sleep(random.uniform(self.min_interval, self.max_interval))
            d = random.choice(["东", "西", "南", "北"])
            special_types = ["消防车", "救护车", "警车"]
            v_type = "普通车"
            if random.random() < 0.3: #True
                v_type = random.choice(special_types)
            vehicle = Vehicle(random.randint(1, 100), d, v_type)
            if vehicle.is_special:
                queues[d]["special"].put(vehicle)
            else:
                queues[d]["ordinary"].put(vehicle)
            add_log(f"【新车生成】{vehicle} -> {d}队列")

class DirectionThread(threading.Thread):
    def __init__(self, direction):
        super().__init__(daemon=True)
        self.direction = direction

    def run(self):
        global ew_green
        while True:
            # 优先处理特权车（非阻塞：为每辆车启动独立线程）
            if not queues[self.direction]["special"].empty():
                vehicle = queues[self.direction]["special"].queue[0]
                add_log(f"🚨 特权通行: {vehicle}")

                # 从队列取出并交给车辆自身线程处理动画与通过生命周期
                v = queues[self.direction]["special"].get()
                threading.Thread(target=v.start_cross_thread, args=(active_vehicles,), daemon=True).start()

                # 保证车队跟驰间隔（特权车更短）
                time.sleep(0.3)

            # 如果没有特权车，处理普通车（遵循红绿灯状态）
            elif not queues[self.direction]["ordinary"].empty():
                vehicle = queues[self.direction]["ordinary"].queue[0]
                can_pass = False

                is_ew = self.direction in ["东", "西"]
                with light_lock:
                    if (is_ew and ew_green) or (not is_ew and not ew_green):
                        can_pass = True

                if can_pass:
                    # 从队列取出并交由车辆线程处理
                    v = queues[self.direction]["ordinary"].get()
                    add_log(f"✅ 绿灯通行: {v}")
                    threading.Thread(target=v.start_cross_thread, args=(active_vehicles,), daemon=True).start()

                    # 普通车的跟驰间隔较长
                    time.sleep(0.6)
                else:
                    # 红灯时阻塞短暂轮询，保持队首判断及时
                    time.sleep(0.2)
            else:
                time.sleep(0.5) # 队列空闲阻塞