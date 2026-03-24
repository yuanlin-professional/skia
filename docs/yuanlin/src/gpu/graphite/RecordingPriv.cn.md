# RecordingPriv - Graphite Recording 内部访问接口

> 源文件: `src/gpu/graphite/RecordingPriv.h`

## 概述

`RecordingPriv` 是 Skia Graphite 中 `Recording` 类的内部特权访问类。`Recording` 代表一次录制完成的 GPU 命令序列，而 `RecordingPriv` 为 Skia 内部组件（如 `Context` 的提交流水线）提供了操作录制内部状态的接口，包括延迟目标设置、懒代理实例化、资源准备和命令提交等关键功能。

## 架构位置

`RecordingPriv` 在 Graphite 的录制-回放架构中处于关键位置：

```
Recorder (录制器)
  └── Recording (录制结果)
        └── RecordingPriv (内部访问窗口)
              ├── TaskList (任务列表)
              ├── TextureProxy (纹理代理, 延迟目标)
              ├── LazyProxies (懒加载代理)
              └── CommandBuffer (命令缓冲区)
```

Recording 是 Recorder 和 Context 之间的传递对象：Recorder 负责录制命令，Recording 作为中间产物被提交到 Context 进行实际执行。

## 主要类与结构体

### `RecordingPriv`

内部特权访问类，遵循 Skia 标准的 Priv 模式：
- 无额外数据成员或虚方法
- 禁止赋值和取地址操作
- 仅由 `Recording` 的友元关系构造

## 公共 API 函数

### 延迟目标管理

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `deferredTargetProxy()` | `TextureProxy*` | 获取延迟渲染目标的纹理代理 |
| `setupDeferredTarget()` | `const Texture*` | 设置延迟目标，关联 Surface 和位移/裁剪参数 |

### 懒代理实例化

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `hasVolatileLazyProxies()` | `bool` | 是否存在易失性懒代理 |
| `instantiateVolatileLazyProxies()` | `bool` | 实例化所有易失性懒代理 |
| `deinstantiateVolatileLazyProxies()` | `void` | 反实例化易失性懒代理 |
| `hasNonVolatileLazyProxies()` | `bool` | 是否存在非易失性懒代理 |
| `instantiateNonVolatileLazyProxies()` | `bool` | 实例化非易失性懒代理 |

### 资源与命令管理

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `prepareResources()` | `bool` | 准备录制所需的 GPU 资源 |
| `addCommands()` | `bool` | 将录制的命令添加到命令缓冲区 |
| `addResourceRef()` | `void` | 添加资源引用以延长其生命周期 |
| `setFailureResultForFinishedProcs()` | `void` | 为完成回调设置失败结果 |

### 状态查询

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `taskList()` | `TaskList*` | 获取根任务列表 |
| `recorderID()` | `uint32_t` | 获取创建此 Recording 的 Recorder ID |
| `uniqueID()` | `uint32_t` | 获取 Recording 的唯一标识符 |

### 测试专用方法（GPU_TEST_UTILS）

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `isTargetProxyInstantiated()` | `bool` | 目标代理是否已实例化 |
| `numVolatilePromiseImages()` | `int` | 易失性 Promise 图像数量 |
| `numNonVolatilePromiseImages()` | `int` | 非易失性 Promise 图像数量 |
| `hasTasks()` | `bool` | 是否包含待处理任务 |

## 内部实现细节

### 资源引用追踪

`addResourceRef()` 方法当前用于追踪 Buffer 资源，最终会在 CommandBuffer 上添加使用引用（Usage Ref）。源码注释指出，如果未来需要追踪 Texture 或 GPU-only Buffer，应维护第二个引用列表以区分不同类型的 CommandBuffer 引用。

### 懒代理分类

- **易失性（Volatile）懒代理**: 每次提交后可以反实例化，对应 Promise Image 等临时资源
- **非易失性（Non-Volatile）懒代理**: 实例化后保持有效，对应持久资源

## 依赖关系

- **include/core/SkPoint.h**: `SkIVector` 类型
- **include/core/SkRefCnt.h**: 引用计数
- **include/gpu/graphite/Recording.h**: 宿主类 `Recording`
- 前向声明: `CommandBuffer`, `Context`, `Resource`, `ResourceProvider`, `RuntimeEffectDictionary`, `ScratchResourceManager`, `Surface`, `TaskList`, `Texture`, `TextureProxy`

## 设计模式与设计决策

### 延迟渲染目标模式

`setupDeferredTarget()` 实现了延迟绑定的渲染目标。Recording 在录制时不需要知道最终的渲染目标，目标在提交到 Context 时才被解析。这支持了 Graphite 的多 Recorder 并行录制架构。

### Promise Image 生命周期管理

易失性/非易失性懒代理的区分体现了 Graphite 对 Promise Image 不同使用模式的优化：
- 易失性代理在每帧重新实例化，适合视频帧等动态内容
- 非易失性代理持久化，适合静态图像资源

## 性能考量

- `taskList()`, `recorderID()`, `uniqueID()` 均为内联函数，零开销访问
- 懒代理的延迟实例化减少了 Recording 阶段的 GPU 内存占用
- 资源引用通过 `sk_sp` 智能指针管理，确保命令执行期间资源不被释放

## 相关文件

- `include/gpu/graphite/Recording.h` - Recording 公共 API
- `src/gpu/graphite/Recording.cpp` - Recording 实现
- `src/gpu/graphite/ContextPriv.h` - Context 内部访问接口
- `src/gpu/graphite/TaskList.h` - 任务列表
- `src/gpu/graphite/TextureProxy.h` - 纹理代理
