# GraphiteTestContext

> 源文件
> - tools/graphite/GraphiteTestContext.h
> - tools/graphite/GraphiteTestContext.cpp

## 概述

GraphiteTestContext 是 Skia Graphite 测试框架的抽象基类,提供跨平台的离屏 3D 上下文管理接口。该类封装了不同 GPU 后端(Metal、Vulkan、Dawn)的测试上下文创建和提交同步逻辑,用于Skia 内部测试而非通用开发。

核心功能:
- 抽象不同 GPU 后端的测试上下文
- 管理 GPU 工作的提交和同步
- 实现帧延迟控制(最多 3 帧未完成)
- 提供同步提交和异步提交接口
- 支持自定义的 tick() 机制推进 GPU 进度

## 架构位置

```
skia/
├── include/
│   ├── core/SkRefCnt.h              # 引用计数
│   └── gpu/graphite/
│       ├── Context.h                 # Graphite 上下文
│       ├── Recording.h               # 记录对象
│       └── GraphiteTypes.h           # Graphite 类型定义
├── src/
│   ├── core/SkTraceEvent.h          # 性能追踪
│   └── gpu/graphite/
│       ├── Caps.h                    # GPU 能力
│       └── ContextPriv.h             # 上下文私有接口
├── tools/
│   ├── gpu/FlushFinishTracker.h     # 完成追踪器
│   └── graphite/
│       ├── GraphiteTestContext.h    # 本模块头文件
│       ├── GraphiteTestContext.cpp  # 本模块实现
│       ├── dawn/GraphiteDawnTestContext.h
│       ├── mtl/GraphiteMtlTestContext.h
│       └── vk/GraphiteVulkanTestContext.h
└── tests/                           # 测试代码
```

在测试架构中的位置:
- 抽象基类,定义测试上下文接口
- 子类实现特定后端(Metal、Vulkan、Dawn)
- 与 `ContextFactory` 配合使用
- 为测试提供统一的 GPU 同步机制

## 主要类与结构体

### GraphiteTestContext
```cpp
class GraphiteTestContext
```
抽象测试上下文基类。

**主要成员**:
- `fFinishTrackers[kMaxFrameLag - 1]`: 完成追踪器数组
- `fCurrentFlushIdx`: 当前 flush 索引
- `kMaxFrameLag = 3`: 最大帧延迟

**纯虚函数**:
- `backend()`: 返回后端类型
- `contextType()`: 返回上下文类型
- `makeContext()`: 创建 Graphite Context

**实现的方法**:
- `submitRecordingAndWaitOnSync()`: 提交记录并等待同步
- `syncedSubmit()`: 同步提交
- `tick()`: 推进 GPU 进度(默认空实现)
- `getMaxGpuFrameLag()`: 获取最大帧延迟

**特性**:
- 禁止拷贝构造和赋值
- 虚析构函数

## 公共 API 函数

### backend() (纯虚)
```cpp
virtual skgpu::BackendApi backend() = 0
```
**功能**: 返回 GPU 后端类型
**返回值**: `BackendApi` 枚举(kMetal、kVulkan、kDawn 等)

### contextType() (纯虚)
```cpp
virtual skgpu::ContextType contextType() = 0
```
**功能**: 返回上下文类型
**返回值**: `ContextType` 枚举(kMetal、kVulkan、kDawn_D3D12 等)

### makeContext() (纯虚)
```cpp
virtual std::unique_ptr<skgpu::graphite::Context> makeContext(const TestOptions&) = 0
```
**功能**: 创建 Graphite Context 实例
**参数**:
- `TestOptions`: 测试选项配置

**返回值**: Context 的唯一指针

### getMaxGpuFrameLag()
```cpp
bool getMaxGpuFrameLag(int *maxFrameLag) const
```
**功能**: 获取最大 GPU 帧延迟数
**参数**:
- `maxFrameLag`: 输出参数,设置为 `kMaxFrameLag` (3)

**返回值**: 总是返回 `true`

### submitRecordingAndWaitOnSync()
```cpp
void submitRecordingAndWaitOnSync(skgpu::graphite::Context* context,
                                   skgpu::graphite::Recording* recording)
```
**功能**: 提交记录并管理帧延迟同步
**参数**:
- `context`: Graphite 上下文
- `recording`: 要提交的记录

**行为**:
1. 如果有 `kMaxFrameLag - 1` 个未完成的提交,等待最早的完成
2. 创建新的完成追踪器
3. 插入记录,附加完成回调
4. 提交(不等待 CPU 同步)
5. 更新循环索引

**用途**: 测试中控制并发 GPU 工作数量

### tick()
```cpp
virtual void tick()
```
**功能**: 允许 GPU API 推进已提交工作的进度
**默认实现**: 空操作

**子类覆盖**: 某些 API(如 Dawn)需要在主线程调用 poll 函数

### syncedSubmit()
```cpp
void syncedSubmit(skgpu::graphite::Context* context)
```
**功能**: 同步提交,确保所有 GPU 工作完成
**参数**:
- `context`: Graphite 上下文

**行为**:
- 如果上下文支持 CPU 同步: 使用 `SyncToCpu::kYes` 提交
- 如果不支持: 使用 `SyncToCpu::kNo` 并忙等待,调用 `tick()` 和 `checkAsyncWorkCompletion()`

**用途**: 测试结束时确保所有工作完成

## 内部实现细节

### 帧延迟管理机制
```cpp
static constexpr int kMaxFrameLag = 3;
sk_sp<sk_gpu_test::FlushFinishTracker> fFinishTrackers[kMaxFrameLag - 1];
int fCurrentFlushIdx = 0;
```

**数组大小**: `kMaxFrameLag - 1 = 2`
- 追踪最多 2 个未完成的 flush
- 允许最多 3 帧的 GPU 工作并发(当前 + 2 个未完成)

**循环索引**:
```cpp
fCurrentFlushIdx = (fCurrentFlushIdx + 1) % std::size(fFinishTrackers);
```
在 0 和 1 之间循环。

### 提交和等待实现
```cpp
void GraphiteTestContext::submitRecordingAndWaitOnSync(
    skgpu::graphite::Context* context,
    skgpu::graphite::Recording* recording) {

    TRACE_EVENT0("skia.gpu", TRACE_FUNC);

    // 1. 等待旧的 flush 完成(如果存在)
    if (fFinishTrackers[fCurrentFlushIdx]) {
        fFinishTrackers[fCurrentFlushIdx]->waitTillFinished([this] { tick(); });
    }

    // 2. 创建新的追踪器
    fFinishTrackers[fCurrentFlushIdx].reset(
        new sk_gpu_test::FlushFinishTracker(context));

    // 3. 增加引用计数(回调持有)
    fFinishTrackers[fCurrentFlushIdx]->ref();

    // 4. 准备插入信息
    skgpu::graphite::InsertRecordingInfo info;
    info.fRecording = recording;
    info.fFinishedContext = fFinishTrackers[fCurrentFlushIdx].get();
    info.fFinishedProc = sk_gpu_test::FlushFinishTracker::FlushFinishedResult;

    // 5. 插入记录
    context->insertRecording(info);

    // 6. 异步提交
    context->submit(skgpu::graphite::SyncToCpu::kNo);

    // 7. 更新索引
    fCurrentFlushIdx = (fCurrentFlushIdx + 1) % std::size(fFinishTrackers);
}
```

**关键设计**:
- 使用 `FlushFinishTracker` 追踪 GPU 完成状态
- 完成回调 `FlushFinishedResult` 会 unref 追踪器
- `waitTillFinished()` 期间调用 `tick()` 推进 API

### 同步提交实现
```cpp
void GraphiteTestContext::syncedSubmit(skgpu::graphite::Context* context) {
    // 1. 检查是否支持 CPU 同步
    skgpu::graphite::SyncToCpu sync =
        context->priv().caps()->allowCpuSync()
            ? skgpu::graphite::SyncToCpu::kYes
            : skgpu::graphite::SyncToCpu::kNo;

    // 2. 提交
    context->submit(sync);

    // 3. 如果不支持同步,忙等待
    if (sync == skgpu::graphite::SyncToCpu::kNo) {
        while (context->hasUnfinishedGpuWork()) {
            this->tick();
            context->checkAsyncWorkCompletion();
        }
    }
}
```

**两种策略**:
- **支持同步**: 直接阻塞等待(如 Vulkan)
- **不支持同步**: 轮询检查(如某些 Metal 配置)

### 性能追踪集成
```cpp
TRACE_EVENT0("skia.gpu", TRACE_FUNC);
```
使用 Skia 的追踪系统记录函数调用,用于性能分析。

## 依赖关系

### Graphite 核心
- `skgpu::graphite::Context`: Graphite GPU 上下文
- `skgpu::graphite::Recording`: 记录对象
- `skgpu::graphite::InsertRecordingInfo`: 插入记录信息
- `skgpu::graphite::SyncToCpu`: 同步枚举

### GPU 类型
- `skgpu::BackendApi`: 后端 API 枚举
- `skgpu::ContextType`: 上下文类型枚举

### 工具组件
- `sk_gpu_test::FlushFinishTracker`: 完成追踪器
- `SkTraceEvent`: 性能追踪宏

### 内部接口
- `skgpu::graphite::Caps`: GPU 能力查询
- `skgpu::graphite::ContextPriv`: 上下文私有接口

### 标准库
- `std::unique_ptr`: 智能指针
- `sk_sp`: Skia 引用计数指针

## 设计模式与设计决策

### 模板方法模式
```cpp
class GraphiteTestContext {
public:
    void submitRecordingAndWaitOnSync(...);  // 具体方法
    virtual void tick() {}                   // 钩子方法
    virtual Backend backend() = 0;           // 抽象方法
};
```
定义算法框架,子类填充细节。

### 策略模式
`tick()` 作为策略钩子:
- **默认策略**: 空操作
- **Dawn 策略**: 调用 `device.Tick()` 或 `instance.ProcessEvents()`

### RAII 资源管理
```cpp
sk_sp<FlushFinishTracker> fFinishTrackers[...];
```
使用智能指针自动管理追踪器生命周期。

### 双缓冲模式
```cpp
fFinishTrackers[kMaxFrameLag - 1];
```
类似双缓冲,实际是"三缓冲":
- 当前正在构建的帧
- 2 个未完成的 GPU 帧

### 回调模式
```cpp
info.fFinishedContext = fFinishTrackers[fCurrentFlushIdx].get();
info.fFinishedProc = FlushFinishTracker::FlushFinishedResult;
```
GPU 完成时调用回调,通知追踪器。

### 适配器模式
不同后端的同步机制差异通过 `tick()` 和 `syncedSubmit()` 适配。

### 防御式编程
```cpp
SkASSERT(context);
SkASSERT(recording);
```
关键参数的断言检查。

## 性能考量

### 帧延迟 vs 吞吐量
```cpp
static constexpr int kMaxFrameLag = 3;
```
**权衡**:
- **延迟**: 3 帧,约 50ms (60 FPS)
- **吞吐量**: 更多并发 GPU 工作
- **内存**: 更多未完成的命令缓冲区

**选择**: 3 是平衡点,减少延迟同时保持吞吐量。

### 同步开销
```cpp
fFinishTrackers[fCurrentFlushIdx]->waitTillFinished([this] { tick(); });
```
**开销类型**:
- CPU 等待 GPU: 主要开销
- `tick()` 调用: 轻量级

**优化**: 仅在达到 `kMaxFrameLag` 时等待。

### 忙等待效率
```cpp
while (context->hasUnfinishedGpuWork()) {
    this->tick();
    context->checkAsyncWorkCompletion();
}
```
**效率**: 低,持续消耗 CPU
**理由**: 测试代码,可接受
**生产环境**: 应使用事件/信号量

### 追踪器开销
```cpp
new sk_gpu_test::FlushFinishTracker(context)
```
每次提交创建追踪器:
- 内存分配
- 引用计数管理

**开销**: 相对于 GPU 提交可忽略。

### 引用计数开销
```cpp
fFinishTrackers[fCurrentFlushIdx]->ref();
```
额外的引用计数操作,确保回调期间追踪器存活。

## 相关文件

### Graphite 核心
- `include/gpu/graphite/Context.h`: Graphite 上下文接口
- `include/gpu/graphite/Recording.h`: 记录对象
- `include/gpu/graphite/GraphiteTypes.h`: 类型定义
- `src/gpu/graphite/Caps.h`: GPU 能力

### 后端实现
- `tools/graphite/dawn/GraphiteDawnTestContext.h`: Dawn 后端
- `tools/graphite/mtl/GraphiteMtlTestContext.h`: Metal 后端
- `tools/graphite/vk/GraphiteVulkanTestContext.h`: Vulkan 后端

### 测试工具
- `tools/gpu/FlushFinishTracker.h`: 完成追踪器
- `tools/graphite/ContextFactory.h`: 上下文工厂
- `tools/graphite/TestOptions.h`: 测试选项

### 性能工具
- `src/core/SkTraceEvent.h`: 性能追踪

### 测试用途
- `tests/`: 使用本类的单元测试
- `gm/`: GM 测试框架
- `dm/`: DM 测试框架
