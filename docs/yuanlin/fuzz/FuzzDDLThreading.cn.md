# DDL 多线程模糊测试

> 源文件: `fuzz/FuzzDDLThreading.cpp`

## 概述

此文件对 DDL（Deferred Display List）的多线程使用场景进行模糊测试。它创建 promise image 数组，并发录制引用这些 promise image 的 DDL，然后在 GPU 线程上回放。这模拟了 Chromium 中实际的多线程渲染架构。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，是 DDL 多线程安全性测试的核心。

## 主要类与结构体

### `PromiseImageInfo`
- 管理单个 promise image 的状态
- `fState` - 原子状态：kInitial -> kTriedToFulfill -> kDone
- `fImage` - promise image 对象
- `fTexture` - 后备纹理
- `fDrawn` - 是否已被绘制

### `DDLFuzzer`
- 模糊测试运行器，管理整个测试生命周期
- 包含 8 个 promise image、4 个录制线程、1 个 GPU 线程
- `fReusableTextures` - 可复用纹理队列

## 公共 API 函数

- `DEF_FUZZ(DDLThreadingGL, fuzz)` - 在 GL 上下文中运行 DDL 线程测试

### DDLFuzzer 方法
- `run()` - 执行 10000 次并发 DDL 录制和回放
- `fulfillPromiseImage()` - promise image 的纹理兑现回调
- `releasePromiseImage()` - promise image 的纹理释放回调

## 内部实现细节

- 4 个录制线程并发录制，每个 DDL 包含 4 个随机选择的 promise image
- GPU 线程负责回放 DDL 和管理纹理
- 纹理可随机复用或删除（由模糊数据决定）
- promise image 回调可随机失败（模拟纹理分配失败）
- 使用 SkTaskGroup 进行线程池管理
- 状态机验证：确保 fulfill 和 release 按正确顺序调用

## 依赖关系

- `include/private/chromium/GrDeferredDisplayList.h` - DDL API
- `include/private/chromium/GrPromiseImageTexture.h` - Promise 纹理
- `include/core/SkExecutor.h` - 线程池

## 设计模式与设计决策

- **生产者-消费者**：录制线程生产 DDL，GPU 线程消费并回放
- **Promise 模式**：promise image 延迟纹理兑现，支持并发录制
- **状态机验证**：通过 `SkASSERT_RELEASE` 验证 promise image 状态转换正确性

## 性能考量

10000 次迭代提供充分的并发冲突覆盖。纹理复用减少 GPU 资源分配。

## 相关文件

- `fuzz/FuzzCreateDDL.cpp` - 单线程 DDL 模糊测试
