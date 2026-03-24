# SkChromeRemoteGlyphCache

> 源文件: `include/private/chromium/SkChromeRemoteGlyphCache.h`

## 概述

SkChromeRemoteGlyphCache 提供了一套远程字形缓存机制，用于在 Chromium 渲染器进程和 GPU 进程之间传输字形数据。该模块通过 SkStrikeServer 和 SkStrikeClient 的配对工作模式，实现了字形数据的序列化传输和远程缓存管理，是 Chromium 跨进程渲染架构的核心组件。

## 架构位置

本模块位于 Skia 的私有 Chromium 专用接口层，属于文本渲染子系统的跨进程通信部分。它与 SkStrikeCache（字形缓存）、SkCanvas（画布）和 sktext::gpu::Slug（文本片段）等模块紧密配合，专门为 Chromium 的多进程架构设计。

## 主要类与结构体

### SkStrikeServer

服务端类，运行在渲染器进程中，负责捕获文本绘制操作并序列化字形数据。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fImpl | std::unique_ptr&lt;SkStrikeServerImpl&gt; | 服务端实现的内部指针 |

**核心接口**:
- `DiscardableHandleManager`: 用于创建和管理可丢弃句柄的接口
- `makeAnalysisCanvas()`: 创建用于分析的画布
- `writeStrikeData()`: 序列化字形数据

### SkStrikeServer::DiscardableHandleManager

句柄管理器接口，负责管理远程客户端上字形条目的生命周期。

**主要职责**:
- 为字形条目创建唯一的句柄 ID
- 锁定和验证句柄状态
- 检测远程句柄是否已被删除

### SkStrikeClient

客户端类，运行在 GPU 进程中，负责接收和反序列化来自服务端的字形数据。

**继承关系**: 无直接继承

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fImpl | std::unique_ptr&lt;SkStrikeClientImpl&gt; | 客户端实现的内部指针 |

### SkStrikeClient::DiscardableHandleManager

客户端句柄管理器，继承自 SkRefCnt，负责删除句柄和报告缓存未命中事件。

**主要职责**:
- 删除不再需要的句柄
- 报告缓存未命中类型
- 处理读取失败的情况

### CacheMissType 枚举

定义了不同类型的缓存未命中情况，用于 Chromium 的直方图报告。

**枚举值**:
| 值 | 说明 |
|-----|------|
| kFontMetrics | 字体度量信息缺失 |
| kGlyphMetrics | 字形度量信息缺失 |
| kGlyphImage | 字形图像缺失 |
| kGlyphPath | 字形路径缺失 |
| kGlyphDrawable | 字形可绘制对象缺失 |

## 公共 API 函数

### `SkStrikeServer::makeAnalysisCanvas()`

```cpp
std::unique_ptr<SkCanvas> makeAnalysisCanvas(int width, int height,
                                            const SkSurfaceProps& props,
                                            sk_sp<SkColorSpace> colorSpace,
                                            bool DFTSupport,
                                            bool DFTPerspSupport = true)
```

- **功能**: 创建一个用于分析的 SkCanvas，所有在该画布上的绘制操作都会被捕获，以便后续序列化
- **参数**:
  - `width/height`: 画布尺寸
  - `props`: 表面属性
  - `colorSpace`: 颜色空间
  - `DFTSupport`: 是否支持距离场文本
  - `DFTPerspSupport`: 是否支持透视距离场文本
- **返回值**: 分析用的画布对象

### `SkStrikeServer::writeStrikeData()`

```cpp
void writeStrikeData(std::vector<uint8_t>* memory)
```

- **功能**: 将通过分析画布捕获的字形数据序列化到提供的内存缓冲区中
- **参数**: `memory` - 用于存储序列化数据的字节向量
- **返回值**: 无
- **副作用**: 调用后，所有通过 DiscardableHandleManager 锁定的句柄将被视为已解锁

### `SkStrikeClient::readStrikeData()`

```cpp
bool readStrikeData(const volatile void* memory, size_t memorySize)
```

- **功能**: 反序列化来自 SkStrikeServer 的字形数据
- **参数**:
  - `memory`: 序列化数据的内存地址
  - `memorySize`: 数据大小
- **返回值**: 成功返回 true，数据无效返回 false
- **注意**: 在栅格化操作之前，必须先反序列化所有相关消息

### `SkStrikeClient::translateTypefaceID()`

```cpp
bool translateTypefaceID(SkAutoDescriptor* descriptor) const
```

- **功能**: 将描述符中的字体 ID 从渲染器进程映射到 GPU 进程
- **参数**: `descriptor` - 需要转换的字体描述符
- **返回值**: 转换成功返回 true
- **用途**: 确保跨进程的字体引用一致性

### `SkStrikeClient::deserializeSlugForTest()`

```cpp
sk_sp<sktext::gpu::Slug> deserializeSlugForTest(const void* data, size_t size) const
```

- **功能**: 从缓冲区反序列化 Slug，并进行字体 ID 转换（仅用于测试）
- **参数**:
  - `data`: 序列化数据
  - `size`: 数据大小
- **返回值**: 成功返回 Slug 对象，失败返回 nullptr

## 内部实现细节

### 数据流程

1. **捕获阶段**: 渲染器进程调用 `makeAnalysisCanvas()` 创建分析画布，所有文本绘制操作被记录
2. **序列化阶段**: 调用 `writeStrikeData()` 将记录的字形数据序列化为字节流
3. **传输阶段**: 序列化数据通过 IPC 传输到 GPU 进程
4. **反序列化阶段**: GPU 进程调用 `readStrikeData()` 恢复字形数据到本地缓存
5. **使用阶段**: GPU 进程使用本地缓存的字形数据进行实际渲染

### 句柄管理机制

SkDiscardableHandleId 是一个 uint32_t 类型的句柄标识符，用于在两个进程间同步字形缓存条目的生命周期：

- **锁定机制**: 服务端创建句柄时处于锁定状态，保证数据在序列化前不会被删除
- **解锁时机**: 调用 `writeStrikeData()` 后，所有句柄自动解锁
- **删除通知**: 客户端通过 `deleteHandle()` 通知服务端可以删除对应的缓存条目

### 缓存未命中处理

当客户端发现所需字形数据不在本地缓存时：

1. 通过 `notifyCacheMiss()` 报告缺失类型和字体大小
2. Chromium 使用这些数据生成直方图，用于性能分析
3. 对于硬失败（如 kFontMetrics），可能需要回退到其他渲染路径

### ReadFailureData 结构

用于报告反序列化失败的详细信息：

| 字段 | 说明 |
|------|------|
| memorySize | 总内存大小 |
| bytesRead | 已读取的字节数 |
| typefaceSize | 字体数据大小 |
| strikeCount | Strike 数量 |
| glyphImagesCount | 字形图像数量 |
| glyphPathsCount | 字形路径数量 |

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt | 智能指针管理 |
| SkTypeface | 字体类型定义 |
| SkCanvas | 画布接口 |
| SkColorSpace | 颜色空间管理 |
| SkStrikeCache | 字形缓存存储 |
| sktext::gpu::Slug | GPU 文本片段 |
| SkAutoDescriptor | 字体描述符 |
| SkSurfaceProps | 表面属性 |

### 被依赖的模块

- Chromium 的渲染器进程：使用 SkStrikeServer 捕获文本绘制
- Chromium 的 GPU 进程：使用 SkStrikeClient 恢复字形数据
- Skia 的 GPU 文本渲染流水线
- Chromium 的性能监控系统（通过 CacheMissType 枚举）

## 设计模式与设计决策

### 客户端-服务端模式

采用配对的 Server/Client 模式设计，清晰地分离了数据生产者和消费者的职责，使得代码易于维护和扩展。

### 句柄管理器接口

通过 DiscardableHandleManager 抽象接口，解耦了句柄生命周期管理的具体实现，允许 Chromium 注入自定义的内存管理策略。

### Pimpl 惯用法

SkStrikeServer 和 SkStrikeClient 都使用 `fImpl` 指针隐藏实现细节，这种设计：
- 减少头文件依赖
- 允许实现细节独立演化
- 保持 API 稳定性

### 不可变性设计

该类标注为"非线程安全"，预期在单线程环境中使用，避免了复杂的同步机制。

## 性能考量

### 批量序列化

`writeStrikeData()` 一次性序列化所有字形数据，减少了 IPC 调用次数，提高了跨进程通信效率。

### 可丢弃缓存

通过句柄机制实现的可丢弃缓存策略，允许在内存压力下释放不常用的字形数据，然后在需要时重新传输。

### 分析画布优化

`makeAnalysisCanvas()` 创建的画布专门用于捕获操作而不实际渲染，避免了不必要的绘制开销。

### 字体 ID 转换

`translateTypefaceID()` 确保字体引用在跨进程环境中的正确性，避免了完整字体数据的重复传输。

### 测试接口隔离

测试相关的方法（如 `setMaxEntriesInDescriptorMapForTesting`）与生产代码分离，保证了性能关键路径的纯净。

## 平台相关说明

该模块专为 Chromium 设计，但实现本身是跨平台的。句柄管理和 IPC 传输的具体实现由 Chromium 层负责，Skia 只提供序列化/反序列化机制。

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/core/SkStrikeCache.h` | 本地字形缓存实现 |
| `src/core/SkStrikeServerImpl.h` | 服务端内部实现 |
| `src/core/SkStrikeClientImpl.h` | 客户端内部实现 |
| `include/core/SkCanvas.h` | 画布接口定义 |
| `include/core/SkTypeface.h` | 字体类型定义 |
| `src/text/gpu/Slug.h` | GPU 文本片段实现 |
