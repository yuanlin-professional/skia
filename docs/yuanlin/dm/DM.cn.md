# DM 主程序

> 源文件: `dm/DM.cpp`

## 概述

DM（Diamond Master）是 Skia 的主要测试和基准测试运行器。此文件实现了 DM 的完整执行流程：配置解析、测试源和渲染目标的创建、多线程测试执行、结果收集和 JSON 报告生成。它是 Skia CI/CD 系统的核心组件。

## 架构位置

位于 `dm/` 目录，是 DM 可执行程序的入口点和主循环。调用 `DMSrcSink.h` 中定义的各种源（Source）和渲染目标（Sink）。

## 主要类与结构体

### `Running`
- `id` - 正在运行的任务标识
- `thread` - 执行线程 ID

### `Gold`
- 继承自 `SkString`，组合 config/src/srcOptions/name/md5 为唯一标识
- 内嵌 `Hash` 结构用于哈希集合

### `TaggedSrc` / `TaggedSink`
- 标记的源和渲染目标，附加类型标签

## 公共 API 函数

- `main()` - 程序入口
- `done()` - 任务完成回调，更新进度并写入 JSON
- `start()` - 任务开始记录
- `fail()` - 记录失败

## 内部实现细节

- 丰富的命令行标志：`--src`（源类型）、`--skip`（跳过规则）、`--match`（名称匹配）、`--threads`（线程数）等
- 使用 `SkSpinlock` 保护并发访问的全局状态（进度、运行任务列表）
- 信号处理：捕获 SIGABRT、SIGBUS、SIGFPE 等信号并输出当前运行任务
- 支持分片执行：`--shards` 和 `--shard` 用于分布式测试
- 黄金结果比较：通过 `dm.json` 文件进行结果追踪
- 支持多种源类型：gm、skp、mskp、lottie、svg、image、colorImage、tests
- 支持 Ganesh 和 Graphite GPU 后端

## 依赖关系

- `dm/DMSrcSink.h` / `dm/DMJsonWriter.h` - 源/渲染目标和 JSON 输出
- `tests/Test.h` - 测试框架
- `tools/` - 各种工具库
- Skia 核心库和 GPU 后端

## 设计模式与设计决策

- **Source-Sink 架构**：将测试输入（Source）和渲染方式（Sink）正交组合
- **进度追踪**：使用自旋锁保护的全局状态实现线程安全的进度报告
- **优雅降级**：信号处理器输出正在运行的任务，帮助定位崩溃原因

## 性能考量

- 多线程执行，默认每核一个额外线程
- 使用 SkTaskGroup 进行任务调度
- 定期（每4秒或每500个任务）写出 JSON 避免数据丢失
- 内存使用监控：定期报告 RSS（常驻内存集）

## 相关文件

- `dm/DMSrcSink.h` / `dm/DMSrcSink.cpp` - 源和渲染目标实现
- `dm/DMJsonWriter.h` - JSON 结果写入器
