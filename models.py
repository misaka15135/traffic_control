import threading
import time

class Vehicle:
    def __init__(self, v_id, direction, v_type="普通车"):
        self.id = str(v_id).zfill(3)
        self.direction = direction
        self.type = v_type
        self.is_special = v_type in ["消防车", "救护车", "警车"]
        
        # 调度时间片：特权车只需 0.5s 就能通过路口，普通车需 1.5s
        self.speed = 0.5 if self.is_special else 1.5
        
        # --- UI 视觉属性 ---
        # 记录开始过马路的时间（用于 GUI 计算动画进度）
        self.start_cross_time = 0
        
        # 分配颜色：救护车(白)、消防车(红)、警车(蓝)、普通车(黄)
        if v_type == "消防车":
            self.color = "#FF4500" # 橘红
        elif v_type == "救护车":
            self.color = "#F0F8FF" # 亮白
        elif v_type == "警车":
            self.color = "#1E90FF" # 亮蓝
        else:
            self.color = "#FFD700" # 金黄

    def __str__(self):
        return f"[{self.direction}向] {self.type} {self.id}号"

    def start_cross(self):
        """记录开始过路的时间（由调度线程/穿越线程调用）。"""
        self.start_cross_time = time.time()

    def start_cross_thread(self, active_list, on_finish=None):
        """
        在独立线程中执行车辆穿越的生命周期：
        - 将车辆加入 active_list（GUI 使用该列表绘制动画）
        - 睡眠 self.speed 模拟通过时间
        - 从 active_list 中移除并调用可选回调
        active_list 必须是线程安全或由主线程/调度线程以谨慎方式访问。
        """
        # 标记开始时间并加入活跃列表
        self.start_cross_time = time.time()
        active_list.append(self)
        try:
            time.sleep(self.speed)
        finally:
            # 确保即使异常也会尝试移除自己
            try:
                active_list.remove(self)
            except ValueError:
                pass
            if on_finish:
                try:
                    on_finish(self)
                except Exception:
                    pass

    def progress(self, current_time=None):
        """返回 0.0~1.0 的过路进度，用于 GUI 位置计算。"""
        if self.start_cross_time == 0:
            return 0.0
        if current_time is None:
            current_time = time.time()
        p = (current_time - self.start_cross_time) / self.speed
        return max(0.0, min(1.0, p))
