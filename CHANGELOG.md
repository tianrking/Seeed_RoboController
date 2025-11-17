# 更新日志 (Change Log)

## v1.1.0 - 串口切换标题修复

### 修复内容 (Fixed)
- 修复了当用户选择不同串口时，面板标题中显示的串口号没有更新的问题
- 修复了副标题中串口信息不会更新的问题，改为显示固定标题文本

### 技术改进 (Technical Improvements)
1. **ServoPanel类新增方法**：
   - 添加了 `update_port_name()` 方法来动态更新面板标题
   - 将标题标签存储为实例变量 `self.title_label`

2. **串口切换逻辑优化**：
   - 改进了 `on_left_port_changed()` 和 `on_right_port_changed()` 方法
   - 从重新创建面板改为更新现有面板，提高效率并保持状态
   - 正确更新工作线程并重新连接信号

3. **界面显示优化**：
   - 串口切换时，面板标题实时更新显示当前选择的串口号
   - 例如：从 "🏭 COM1 - 舵机标定" 更新为 "🏭 COM99 - 舵机标定"
   - 副标题改为固定文本："双串口工厂舵机标定工具 - 支持中位校准、测试、失能功能"
   - 避免了串口信息显示不一致的问题

### 测试结果
- 所有依赖检查通过 ✓
- 文件完整性验证通过 ✓
- 语法检查通过 ✓
- 串口切换功能正常工作 ✓

### 使用方法
```bash
# 运行主程序
python factory_calibration_tool.py

# 或指定串口
python factory_calibration_tool.py --port1 COM1 --port2 COM2

# 列出可用串口
python factory_calibration_tool.py --list-ports
```

现在当您在UI中选择不同的串口时，左右两个面板的标题会立即更新显示当前选择的串口号，提供更直观的用户体验。