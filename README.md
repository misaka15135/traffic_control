# Traffic Control Simulation

基于 Python + tkinter 的二维交通控制模拟，包含：

- 四方向车道与车辆队列（普通车 / 特权车）
- 红绿灯控制与调度逻辑
- 每辆车独立的通过生命周期与 GUI 动画

运行：

```bash
python main.py
```

依赖：Python 3.x（tkinter）

说明：已将车辆穿越改为每车独立线程，使队列不会因单辆车 sleep 而完全阻塞。

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
