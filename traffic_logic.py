import threading
import time
import random
import queue
from models import Vehicle

ew_green = True
light_lock = threading.Lock()

# 单一队列：每个方向一个 queue.Queue()
queues = {
    "东": queue.Queue(),
    "西": queue.Queue(),
    "南": queue.Queue(),
    "北": queue.Queue()
}


def promote_special_in_queue(direction, vehicle, delay=0.3):
    """当特权车进入队列后，独立线程每隔 delay 检查前方一辆车：
    如果前车是普通车则与其互换位置，直到到达队首或前车也为特权车或车辆离队。
    使用 queue.Queue 的内部 mutex 与 .queue（deque）直接操作以保证原子性。
    """
    q = queues[direction]
    while True:
        time.sleep(delay)
        with q.mutex:
            try:
                idx = q.queue.index(vehicle)
            except ValueError:
                # 车辆已离开队列
                break
            if idx == 0:
                # 已经到队首
                break
            prev = q.queue[idx - 1]
            if not prev.is_special:
                # 互换位置
                q.queue[idx - 1], q.queue[idx] = q.queue[idx], q.queue[idx - 1]
                add_log(f"↗ 特权车 {vehicle} 与普通车 {prev} 互换位置")
            # 继续循环，直到条件不满足或车辆离队


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
            for _ in range(4):  # 初始每条路排4辆车
                v_type = "普通车"
                if random.random() < 0.3:
                    v_type = random.choice(special_types)
                vehicle = Vehicle(random.randint(1, 100), d, v_type)
                queues[d].put(vehicle)
                if vehicle.is_special:
                    threading.Thread(target=promote_special_in_queue, args=(d, vehicle, 0.3), daemon=True).start()

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
            if random.random() < 0.3:
                v_type = random.choice(special_types)
            vehicle = Vehicle(random.randint(1, 100), d, v_type)
            # 统一放入单一队列
            queues[d].put(vehicle)
            # 如果是特权车，启动提升尝试线程（非阻塞）
            if vehicle.is_special:
                threading.Thread(target=promote_special_in_queue, args=(d, vehicle, 0.3), daemon=True).start()
            add_log(f"【新车生成】{vehicle} -> {d}队列")


class DirectionThread(threading.Thread):
    def __init__(self, direction):
        super().__init__(daemon=True)
        self.direction = direction

    def run(self):
        global ew_green
        while True:
            q = queues[self.direction]
            # 安全地查看队首元素
            with q.mutex:
                if len(q.queue) == 0:
                    front = None
                else:
                    front = q.queue[0]

            if front is not None and front.is_special:
                add_log(f"🚨 特权通行: {front}")
                v = q.get()
                threading.Thread(target=v.start_cross_thread, args=(active_vehicles,), daemon=True).start()
                time.sleep(0.3)

            elif front is not None:
                can_pass = False
                is_ew = self.direction in ["东", "西"]
                with light_lock:
                    if (is_ew and ew_green) or (not is_ew and not ew_green):
                        can_pass = True

                if can_pass:
                    v = q.get()
                    add_log(f"✅ 绿灯通行: {v}")
                    threading.Thread(target=v.start_cross_thread, args=(active_vehicles,), daemon=True).start()
                    time.sleep(0.6)
                else:
                    time.sleep(0.2)
            else:
                time.sleep(0.5)
