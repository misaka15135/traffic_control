import tkinter as tk
import time
import traffic_logic

class TrafficGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("操作系统项目: 二维交通控制模拟")
        self.root.geometry("850x600")
        self.root.configure(bg="#2b2b2b")

        # 左侧：二维画布区 (600x600)
        self.canvas = tk.Canvas(root, width=600, height=600, bg="#3c3f41", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT)

        # 右侧：实时日志区
        self.text_area = tk.Text(root, height=35, width=32, bg="#1e1e1e", fg="#a9b7c6", font=("Consolas", 10))
        self.text_area.pack(side=tk.RIGHT, padx=10, pady=10)

        self.draw_static_background()
        self.update_gui()

    def draw_static_background(self):
        """绘制静态的十字路口背景"""
        c = self.canvas
        # 绘制马路 (深灰色)
        c.create_rectangle(240, 0, 360, 600, fill="#555555", outline="") # 南北向马路
        c.create_rectangle(0, 240, 600, 360, fill="#555555", outline="") # 东西向马路
        
        # 绘制马路中心虚线
        c.create_line(300, 0, 300, 240, fill="#dddddd", dash=(10,10), width=2)
        c.create_line(300, 360, 300, 600, fill="#dddddd", dash=(10,10), width=2)
        c.create_line(0, 300, 240, 300, fill="#dddddd", dash=(10,10), width=2)
        c.create_line(360, 300, 600, 300, fill="#dddddd", dash=(10,10), width=2)

        # 绘制四个角的停止线
        c.create_line(240, 240, 300, 240, fill="white", width=4) # 北向南停止线
        c.create_line(300, 360, 360, 360, fill="white", width=4) # 南向北停止线
        c.create_line(240, 300, 240, 360, fill="white", width=4) # 西向东停止线
        c.create_line(360, 240, 360, 300, fill="white", width=4) # 东向西停止线

    def update_gui(self):
        # 清除上一帧的动态元素
        self.canvas.delete("dynamic")

        # 1. 绘制红绿灯状态
        ew_color = "#00FF00" if traffic_logic.ew_green else "#FF0000"
        sn_color = "#FF0000" if traffic_logic.ew_green else "#00FF00"
        
        # 东西向红绿灯
        self.canvas.create_oval(215, 315, 230, 330, fill=ew_color, tags="dynamic") # 西路口
        self.canvas.create_oval(370, 270, 385, 285, fill=ew_color, tags="dynamic") # 东路口
        # 南北向红绿灯
        self.canvas.create_oval(270, 215, 285, 230, fill=sn_color, tags="dynamic") # 北路口
        self.canvas.create_oval(315, 370, 330, 385, fill=sn_color, tags="dynamic") # 南路口

        # 2. 绘制排队等候的车辆（使用方块表示）
        # 单一队列：按队列顺序渲染，特权车在队列中间会被标记为 S
        def render_direction(dir_key, base_x, base_y, step, horizontal=True):
            q_list = list(traffic_logic.queues[dir_key].queue)
            for idx, v in enumerate(q_list):
                if horizontal:
                    x = base_x + idx * step
                    y = base_y
                else:
                    x = base_x
                    y = base_y + idx * step
                self.draw_vehicle_block(v, x, y)

        # 西向东（左到右），base_x=200, step=-35
        render_direction("西", 200, 310, -35, horizontal=True)
        # 东向西（右到左），base_x=370, step=35
        render_direction("东", 370, 250, 35, horizontal=True)
        # 北向南（上到下），base_y=200, step=-35
        render_direction("北", 250, 200, -35, horizontal=False)
        # 南向北（下到上），base_y=370, step=35
        render_direction("南", 310, 370, 35, horizontal=False)

        # 3. 绘制正在路口中行驶的车辆（平滑动画）
        current_time = time.time()
        # 复制列表防止线程修改导致遍历报错
        for v in list(traffic_logic.active_vehicles): 
            # 根据线程等待的时间进度 (0.0 ~ 1.0) 计算坐标
            progress = (current_time - v.start_cross_time) / v.speed
            progress = max(0, min(1, progress)) 
            
            if v.direction == "西": # 向东走
                self.draw_vehicle_block(v, 200 + progress * 200, 310)
            elif v.direction == "东": # 向西走
                self.draw_vehicle_block(v, 370 - progress * 200, 250)
            elif v.direction == "北": # 向南走
                self.draw_vehicle_block(v, 250, 200 + progress * 200)
            elif v.direction == "南": # 向北走
                self.draw_vehicle_block(v, 310, 370 - progress * 200)

        # 4. 刷新日志区
        self.text_area.delete('1.0', tk.END)
        for msg in traffic_logic.log_messages:
            self.text_area.insert(tk.END, msg + "\n")

        # 50毫秒刷新一次界面，实现 20FPS 的流畅动画
        self.root.after(50, self.update_gui)

    def draw_vehicle_block(self, v, x, y):
        """在指定坐标绘制车辆方块"""
        size = 25
        # 绘制车身方块
        self.canvas.create_rectangle(x, y, x+size, y+size, fill=v.color, outline="black", tags="dynamic")
        # 特权车打上 "S" (Special) 标记
        if v.is_special:
             self.canvas.create_text(x + size/2, y + size/2, text="S", fill="black", font=("Arial", 10, "bold"), tags="dynamic")