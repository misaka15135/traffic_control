# Traffic Control Simulation (二维交通控制模拟)

概述

这是一个基于 Python 和 tkinter 的二维十字路口交通控制模拟器。项目演示了车辆生成、队列调度、信号灯控制与 GUI 动画的基本配合，并实现了「每辆车独立生命周期线程」以避免调度线程被单车长时间阻塞的问题。

主要特性

- 四方向路口（东/西/南/北）的车辆队列，区分普通车与特权车（消防车/救护车/警车）。
- 红绿灯周期控制（可配置），东西向与南北向交替放行。
- 特权车优先级更高，优先通行。
- 每辆车在自身线程中执行通过路口的生命周期（记录开始时间、睡眠模拟通过耗时、结束时从活跃列表移除），从而使调度线程只负责发车，不被单车占用。
- GUI 使用 tkinter 绘制静态路面与动态车辆动画，GUI 主线程读取来自调度模块的 active_vehicles 列表以作平滑动画显示。

目录结构

- main.py
  - 程序入口：启动控制器线程（信号灯与车辆生成）与四个方向的调度线程，然后启动 tkinter GUI 主循环。

- traffic_logic.py
  - 调度与模拟核心：
    - ControllerThread：初始化车队与周期性切换红绿灯（按全局变量 ew_green）并启动 VehicleGeneratorThread。
    - VehicleGeneratorThread：按随机间隔生成新车并放入对应方向的队列（ordinary / special）。
    - DirectionThread：每个方向一个线程，检查队列队首并在满足条件时取出车辆，然后为车辆启动车辆线程让其执行穿越生命周期（避免长时间阻塞调度线程）。
    - 使用线程安全的 queue.Queue 存放每个方向的普通/特权队列。

- models.py
  - Vehicle 类：车辆属性（id、方向、类型、速度、颜色等）、start_cross_time 与 start_cross_thread(active_list, on_finish=None) 方法。start_cross_thread 在独立线程中：
    - 记录 start_cross_time
    - 将自己加入 active_vehicles（GUI 用于绘制）
    - sleep(self.speed) 模拟通过耗时
    - 从 active_vehicles 中移除并调用可选回调

- gui_display.py
  - TrafficGUI：tkinter GUI，负责绘制静态道路、信号灯、排队车辆与 active_vehicles 中正在通过的车辆（根据车辆的 start_cross_time 与 speed 计算 progress 并定位）。GUI 以 20 FPS（root.after(50, ...)）更新界面与日志。

设计与并发说明

原实现问题
- 调度线程在取车后直接 time.sleep(v.speed) 以模拟车辆通过时间，导致该方向的调度线程在车辆通过期间被阻塞，队列内其他车辆必须等待调度线程恢复，出现“不符合实际的一个车走完才能下一辆启动”的行为。

改进方法
- 将车辆的“穿越生命周期”移动到车辆自身的线程（models.Vehicle.start_cross_thread），调度线程仅负责决定何时发车（从队列取出并启动车辆线程），然后以短间隔继续处理队列。这样队列可以更接近真实的车流行为，尾随车辆可以在前车刚起步后继续启动。

注意事项
- active_vehicles 列表由多个线程修改（车辆线程 append/remove），GUI 线程读取它以绘制。当前实现依赖于 Python 的 list 原子性/短期一致性来避免复杂同步；若出现并发问题，可用 threading.Lock 或者 collections.deque 并进行适当加锁以保证线程安全。

运行方式

1. 确保已安装 Python 3.x（tkinter 在大多数发行版中默认可用）。
2. 进入项目目录并运行：

```bash
python main.py
```

3. 窗口打开后可以观察车辆生成、排队与通过情况。日志区会显示信号切换与车辆事件。

扩展建议

- 更精细的车间距与避碰逻辑：使用每条路的 Condition/Lock 与车辆间最小跟驰时间或位置检查。
- 支持左转/右转与冲突矩阵：当前实现假定直行，加入转向会显著增加冲突判断逻辑。
- 可视化改进：显示速度、ID、队列长度统计，增加暂停/单步功能。
- 性能：在车辆非常多时，改用更高效的数据结构或引入 asyncio 版本以降低线程开销。

许可证 & 致谢

本示例代码用于教育与演示目的。

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
