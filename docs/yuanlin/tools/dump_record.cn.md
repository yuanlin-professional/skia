# dump_record - SkRecord 命令转储工具

> 源文件: `tools/dump_record.cpp`

## 概述

`dump_record` 读取 SKP 文件并转储其内部 SkRecord 绘图命令列表。支持优化前后的对比、命令计时、写入优化后的 SKP。SaveLayer 命令以红色粗体高亮显示以便识别性能热点。

## 架构位置

属于 Skia 调试和性能分析工具链。

## 主要类与结构体

- **`Dumper`**: 命令访问者,对每条记录执行绘制并打印耗时

## 公共 API 函数

- **`main()`**: 解析 SKP、可选优化、转储命令列表

## 内部实现细节

- 使用 visitor 模式遍历 SkRecord 中的所有命令
- 支持嵌套(Save/Restore 缩进、DrawPicture 递归)
- 命令计时使用 `SkTime::GetNSecs()`
- NoOp 命令静默跳过
- `--optimize` 运行 `SkRecordOptimize` 优化记录
- `--write` 将优化后的 SKP 写回文件

## 依赖关系

- `src/core/SkRecord.h`, `SkRecordCanvas.h`, `SkRecordDraw.h`, `SkRecordOpts.h`
- `tools/flags/CommandLineFlags.h`

## 设计模式与设计决策

- **Visitor 模式**: 通过模板 operator() 分发到各命令类型的 print 方法
- **ANSI 颜色**: SaveLayer 使用终端转义序列红色高亮

## 性能考量

计时包含实际绘制开销,但在单个 Canvas 上绘制可能与实际渲染性能不同。

## 相关文件

- `tools/skp_parser.cpp` - SKP JSON 解析
