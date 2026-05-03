import tkinter as tk
from traffic_logic import ControllerThread, DirectionThread
from gui_display import TrafficGUI

def main():
    print("正在初始化交通控制系统...")

    # 1. 创建并启动任务 1（总控：红绿灯与车辆调度）
    controller = ControllerThread()
    controller.start()

    # 2. 创建并启动任务 2~5（四个方向的处理线程）
    directions = ["东", "西", "南", "北"]
    for d in directions:
        # 为每个方向实例化一个单独的线程
        t = DirectionThread(d)
        t.start()

    # 3. 启动 UI 主线程
    root = tk.Tk()
    app = TrafficGUI(root)
    # mainloop 会阻塞当前主线程，保持窗口显示，直到用户关闭窗口
    root.mainloop()

if __name__ == "__main__":
    main()