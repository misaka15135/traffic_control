# Traffic Control Simulation (二维交通控制模拟)


目录

1. 概述
2. 设计目标与动机
3. 功能与特性（详细）
4. 系统架构概览
5. 代码组件说明
   - main.py
   - traffic_logic.py
   - models.py
   - gui_display.py
6. 数据结构与并发模型
   - 队列实现
   - active_vehicles 管理
   - 日志缓冲
7. 特权车提升算法详解
8. GUI 渲染与动画细节
9. 配置项、参数与调整建议
10. 构建与运行（开发/发布）
11. 测试建议与验证场景
12. 已知问题与安全/并发注意事项
13. 扩展方向与改进建议
14. 许可证与致谢

---

1. 概述

本项目模拟一个四方向（东/西/南/北）的十字路口交通控制系统。使用 Python 多线程模拟车辆生成、调度与通行，Tkinter 提供二维可视化界面。近期改进包括将每方向从原来的普通/特权两个队列合并为单一 FIFO 队列，并实现特权车的“逐步提升”机制，通过局部互换逐步把特权车提升为优先队首，以更贴近真实调度场景。

2. 设计目标与动机

- 教学目标：通过可视化演示让学生理解进程/线程并发调度、互斥、优先级抢占等操作系统概念。
- 真实感：通过让特权车逐步通过队列交换提升而非瞬时跳到队首，展示在线调度中优先级竞争的细粒度行为。
- 简洁性：使用标准库（threading, queue, tkinter）实现，避免复杂依赖，便于教学与移植。

3. 功能与特性（详细）

- 随机车辆生成（普通/特权）
- 每方向单一 FIFO 队列（queue.Queue）
- 特权车逐步提升（promote_special_in_queue）
- 红绿灯周期控制（默认 8 秒切换）
- GUI 实时渲染：静态路面、红绿灯、排队车辆、路口中行驶车辆、日志面板
- 车辆独立生命周期线程，调度线程非阻塞发车
- 日志缓冲显示最近若干条事件（默认 15 条）

4. 系统架构概览

主要线程类型：

- ControllerThread：总控，初始化、红绿灯周期切换、启动车辆生成器
- VehicleGeneratorThread：随机生成车辆并入队（若为特权车则发起提升线程）
- DirectionThread（4 个）：每个方向一个，负责查看队首并决定发车
- Vehicle lifecycle threads：每辆发车后创建，用于在独立线程中 sleep(self.speed) 模拟通过过程
- GUI 主线程：Tkinter 主循环，定时读取调度模块状态并重绘

5. 代码组件说明

main.py
- 程序入口
- 创建并启动 ControllerThread
- 为每个方向创建并启动 DirectionThread
- 启动 Tkinter GUI（TrafficGUI）

traffic_logic.py
- 全部调度逻辑的实现：
  - 全局变量 ew_green: 表示当前东西向是否为绿
  - light_lock: 用于切换与读取灯状态的互斥锁
  - queues: dict，四个方向的 queue.Queue
  - promote_special_in_queue(direction, vehicle, delay): 特权车提升实现
  - ControllerThread / VehicleGeneratorThread / DirectionThread 的实现
- 关键点：DirectionThread 只查看队首元素，若队首是特权车则无视灯色直接发车；普通车则依据 ew_green 放行

models.py
- Vehicle 类
  - 字段：id、direction、type、is_special、speed、color、start_cross_time
  - 方法：start_cross_thread(active_list, on_finish=None)
    - 标记开始时间，加入 active_list，sleep(self.speed)，最后从 active_list 中移除并可回调

gui_display.py
- TrafficGUI 类
  - Canvas 用于绘制路面与车辆
  - Text widget 用于显示日志
  - update_gui: 每 50ms 刷新一次（20 FPS），绘制红绿灯、队列内车辆、active_vehicles 中的行驶车辆并更新日志
  - draw_vehicle_block: 绘制带颜色的方块并对特权车绘制 S 标记

6. 数据结构与并发模型

队列实现
- 使用 queue.Queue（内部基于 collections.deque 并带有 mutex 与条件变量）作为每方向的 FIFO 队列。
- 对于需要读取/修改队列内部结构（如 promote_special_in_queue 的互换），在 q.mutex 上进行保护并直接访问 q.queue（deque）以实现原子性操作。

active_vehicles 管理
- active_vehicles 是一个普通 list，车辆线程 append/remove，GUI 线程读取用于动画。
- 当前实现依赖 Python list 在常见操作上的短期一致性；若需更严格保证，建议改为由 threading.Lock 保护的 list 或者使用线程安全集合。

日志缓冲
- log_messages 用作循环缓冲（保留最近 15 条）；线程安全性由小粒度追加/截断保障，若日志写入密集可加锁。

7. 特权车提升算法详解

目标：当特权车入队且不是队首时，每隔一个短时间片检查前方一辆车，若为普通车则与其交换位置；通过重复此局部交换，特权车最终将到达队首。

算法实现（promote_special_in_queue）要点：
- 当生成器将特权车放入 queues[direction] 后，启动一个守护线程 promote_special_in_queue(direction, vehicle, delay)
- 该线程循环：
  - sleep(delay)
  - 在 q.mutex 保护下尝试定位 vehicle 在 q.queue 中的索引 idx
  - 若 idx 为 0 或 vehicle 不在队列（ValueError），线程结束
  - 检查前一辆 prev，如果 prev.is_special 为 False，则交换 q.queue[idx-1] 与 q.queue[idx]
  - 每次交换后写日志记录交换事件
- 复杂度：在最坏情况下，特权车需要与每辆普通车各做一次 O(1) 的局部交换，总体移动步数等于其提升的格数
- 参数：delay 可调节，越小提升越及时但竞争更频繁；建议 0.2~0.5 秒之间取值以平衡视觉效果与并发成本

线程安全说明：
- q.mutex 能保证对 q.queue 的原子读写
- 只在小临界区内做索引与交换，避免长时间持锁

8. GUI 渲染与动画细节

渲染循环
- GUI 每 50ms 调用 update_gui
- 绘制顺序：清除上一帧动态元素 -> 画红绿灯 -> 渲染队列车辆 -> 渲染 active_vehicles -> 更新日志

队列渲染策略
- 直接把 queue.Queue().queue 转为 list 并按顺序绘制方块
- 特权车以不同颜色并标注 S

active_vehicles 动画
- 车辆在 start_cross_thread 中记录 start_cross_time 并 sleep(self.speed)
- GUI 使用 (current_time - start_cross_time) / speed 得到 progress，并根据方向映射到屏幕坐标实现平滑插值动画

视觉建议
- 队列长度过长时，方块会超出画布。可改进为缩放或仅渲染前 N 辆。
- 可加入过渡动画（位置平滑）提升视觉连贯性。

9. 配置项、参数与调整建议

代码中易调参数：
- 红绿灯周期：traffic_logic.ControllerThread 中的 time.sleep(8) 可改为变量
- 车辆生成间隔：VehicleGeneratorThread(min_interval, max_interval)
- promote delay：promote_special_in_queue 的 delay（默认 0.3s）
- 车辆速度：models.Vehicle 中 speed 根据 is_special 赋值
- GUI 刷新间隔：gui_display.py 中 root.after(50, ...)

推荐默认配置（教学用途）
- 红绿灯周期：8s
- 生成间隔：0.2~1.5s
- promote delay：0.3s
- 特权速度：0.5s，普通速度：1.5s

10. 构建与运行（开发/发布）

开发运行：

```bash
python main.py
```

生成 Windows 可执行：

```bash
python -m PyInstaller --onefile --name traffic_control main.py
```

或使用项目中生成的 .spec（若存在）进行更复杂打包：

```bash
python -m PyInstaller traffic_control.spec
```

构建产物位于 dist/ 下（dist/traffic_control.exe）。打包时注意：Tkinter 及相关 DLL 需要被正确包含，PyInstaller 通常能自动处理，但若出现缺少 Tcl/Tk 资源的问题，可参考 PyInstaller 文档将 Tcl/Tk 目录显式打包。

11. 测试建议与验证场景

基础测试：
- 启动程序，观察 GUI 是否渲染、能否生成车辆、日志是否输出
- 快速生成大量车辆，观察系统稳定性与 GUI 性能

功能验证：
- 特权车优先：在特定方向连续生成普通车，再注入特权车，观察是否逐步提升并在队首优先发车
- 红绿灯交替控制：观察东西/南北方向的交替放行与日志
- active_vehicles 动画：观察车辆平滑通过动画（特权车更快）

并发边界测试：
- 将 promote delay 设为很小（0.05s），观察是否出现锁竞争或 GUI 卡顿
- 大量车辆并发生成，观察内存与线程数是否激增（可在开发环境限制生成速率进行测试）

12. 已知问题与安全/并发注意事项

- active_vehicles 未加显式锁，理论上在极端并发下可能出现 IndexError 或动画异常。建议添加 Lock 或使用线程安全结构。
- 直接访问 queue.Queue().queue 虽常见但被视为内部实现细节；若将来 Python 实现更改，相关代码可能失效。若担心兼容性，可在外层维护一个自定义线程安全 deque 并提供受限 API 以替代直接访问。
- promote_special_in_queue 频繁交换会导致频繁日志写入，日志缓冲应考虑批量或速率限制以减少 IO 压力。

13. 扩展方向与改进建议

- 避免直接访问 q.queue：用自定义类封装队列与安全的 swap API
- 引入车辆位置模型：使用精确 x/y 坐标与碰撞检测替代格子渲染
- 支持转向（左转/右转）并引入冲突矩阵与路口占用资源模型
- 优化线程数量：用线程池或 asyncio 实现以减少大量短命线程开销
- 增加控制面板：调整生成速率、灯周期、promote 参数的实时 UI 控制
- 添加录制/回放功能以用于教学演示

14. 许可证与致谢

本项目为学术课程设计代码，归作者所有。代码中引用的第三方工具（PyInstaller）遵循其各自许可证。感谢操作系统课程组与开源工具提供者。

---

附录：重要文件路径

- 主脚本: main.py
- 调度逻辑: traffic_logic.py
- 车辆模型: models.py
- GUI: gui_display.py
- 打包说明: 使用 PyInstaller 或项目中生成的 .spec