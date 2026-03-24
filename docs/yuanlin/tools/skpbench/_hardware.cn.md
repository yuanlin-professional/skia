# Hardware - 基准测试硬件控制基类

> 源文件: `tools/skpbench/_hardware.py`

## 概述

_hardware.py 定义了基准测试硬件控制的基础框架，包括 Hardware 基类、HardwareException 异常类和 Expectation 验证工具。Hardware 类通过 Python 上下文管理器协议（with 语句）控制硬件进入和退出基准测试模式。

## 架构位置

位于 `tools/skpbench/` 目录，是所有设备硬件控制类的基类。

## 主要类与结构体

### `Hardware`
- 上下文管理器基类，`__enter__`/`__exit__` 为空操作
- `warmup_time` 属性控制预热时间
- `filter_line` 过滤输出行
- `sanity_check` 验证硬件状态

### `HardwareException`
包含 `sleeptime` 属性，指示在异常后应等待多少秒才能恢复。

### `Expectation`
硬件读数验证器，支持最小值、最大值和精确值检查。`check_all` 静态方法批量验证一组读数。

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `Hardware.sanity_check()` | 验证硬件状态 |
| `Hardware.filter_line(line)` | 过滤输出 |
| `Expectation.check(stringvalue)` | 验证单个读数 |
| `Expectation.check_all(expectations, values)` | 批量验证 |

## 内部实现细节

- Expectation 支持类型转换（int/str/long），验证前将字符串转为目标类型
- HardwareException 的 sleeptime 默认 60 秒，电池低电量时为 30 分钟

## 依赖关系

- Python 标准库: `time`

## 设计模式与设计决策

- **上下文管理器**: 确保硬件在测试结束后恢复正常状态
- **策略模式**: 子类覆写方法提供设备特定行为

## 性能考量

设计目标是确保基准测试结果的可重复性，而非自身的执行效率。

## 相关文件

- `_hardware_android.py` - Android 平台实现
- `_hardware_pixel.py`, `_hardware_pixel2.py` 等 - 设备特定实现
