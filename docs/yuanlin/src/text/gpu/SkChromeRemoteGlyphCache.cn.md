# SkChromeRemoteGlyphCache

> 源文件: `src/text/gpu/SkChromeRemoteGlyphCache.cpp`

## 概述

`SkChromeRemoteGlyphCache` 实现了 Chromium 浏览器中文本渲染的远程字形缓存系统。该系统采用客户端-服务器架构,将文本渲染分为两个阶段:在 Renderer 进程中进行字形分析和序列化(服务器端),然后在 GPU 进程中进行反序列化和实际渲染(客户端)。这种设计适配了 Chromium 的多进程架构,确保字形数据能够安全、高效地在进程间传输。

该文件包含四个核心组件:服务器端的 `SkStrikeServer` 及其实现类 `SkStrikeServerImpl`,客户端的 `SkStrikeClient` 及其实现类 `SkStrikeClientImpl`,以及用于字形追踪的 `GlyphTrackingDevice` 和远程打击缓存 `RemoteStrike`。

## 架构位置

```
Chromium Renderer 进程                    Chromium GPU 进程
┌─────────────────────────┐              ┌─────────────────────────┐
│  SkStrikeServer         │              │  SkStrikeClient         │
│  ├─ SkStrikeServerImpl  │  序列化数据   │  ├─ SkStrikeClientImpl  │
│  ├─ GlyphTrackingDevice │ ──────────>  │  ├─ DiscardableStrike   │
│  └─ RemoteStrike        │              │  │   Pinner              │
│                         │              │  └─ SkStrikeCache        │
└─────────────────────────┘              └─────────────────────────┘
```

该模块位于 Skia 文本渲染管线的 GPU 文本子系统中,依赖 `SubRunContainer` 进行子运行计算,并通过 `StrikeForGPU` 接口与底层的字形缓存系统交互。

## 主要类与结构体

### `StrikeSpec` (内部结构体)
- 轻量级结构体,包含 `SkTypefaceID` 和 `SkDiscardableHandleId`
- 用于远程打击缓存的标识

### `RemoteStrike`
- 继承自 `sktext::StrikeForGPU`,是远程字形缓存的核心实现
- 管理待发送的字形掩码(`fMasksToSend`)、路径(`fPathsToSend`)和可绘制对象(`fDrawablesToSend`)
- 使用 `SkArenaAllocWithReset` 进行内存管理
- 通过 `SkGlyphDigest` 哈希表(`fSentGlyphs`)追踪已发送的字形,避免重复传输

### `SkStrikeServerImpl`
- `SkStrikeServer` 的内部实现,继承 `StrikeForGPUCacheInterface`
- 使用 `std::unordered_map` 将 `SkDescriptor` 映射到 `RemoteStrike`
- 维护最大条目数限制(默认 2000),超限时清理已删除的条目
- 追踪已缓存的 `SkTypefaceID` 集合和待发送的字体原型

### `GlyphTrackingDevice`
- 继承自 `SkNoPixelsDevice`,是一种"分析画布"使用的设备
- 拦截 `onDrawGlyphRunList` 调用,执行子运行计算但不产生实际输出
- 支持将 `GlyphRunList` 转换为 `Slug` 以供远程渲染

### `DiscardableStrikePinner`
- 继承自 `SkStrikePinner`,用于客户端的打击缓存条目管理
- 通过 `DiscardableHandleManager` 控制缓存条目的生命周期

### `SkStrikeClientImpl`
- `SkStrikeClient` 的内部实现
- 维护服务器端字体 ID 到客户端字体的映射(`fServerTypefaceIdToTypeface`)
- 内部定义了 `PictureBackedGlyphDrawable` 用于支持基于 SkPicture 的字形可绘制对象

## 公共 API 函数

### SkStrikeServer
- `SkStrikeServer(DiscardableHandleManager*)`: 构造函数,接收可丢弃句柄管理器
- `makeAnalysisCanvas(width, height, props, colorSpace, DFTSupport, DFTPerspSupport)`: 创建分析画布,用于收集字形数据。根据平台设置不同的路径渲染字体大小阈值(Android: 384, Mac: 256, 其他: 324)
- `writeStrikeData(std::vector<uint8_t>*)`: 将收集的字形数据序列化到内存缓冲区

### SkStrikeClient
- `SkStrikeClient(sk_sp<DiscardableHandleManager>, isLogging, strikeCache)`: 构造函数
- `readStrikeData(memory, memorySize)`: 从内存缓冲区反序列化字形数据
- `translateTypefaceID(SkAutoDescriptor*)`: 将服务器端字体 ID 翻译为客户端字体 ID
- `deserializeSlugForTest(data, size)`: 测试用,反序列化 Slug 对象

## 内部实现细节

### 序列化协议
写入顺序:
1. 新发现的字体原型数量及数据 (`fTypefacesToSend`)
2. 包含待发送字形的打击数量
3. 每个打击的数据:字体 ID、可丢弃句柄 ID、描述符、字体度量(仅首次)、字形数据(掩码/路径/可绘制对象)

### 反序列化流程
1. 读取字体原型并创建 `SkTypefaceProxy`
2. 读取打击数据:验证字体 ID、句柄 ID、描述符
3. 翻译字体 ID(服务器端 -> 客户端)
4. 查找或创建 `SkStrike`,合并字形数据
5. 详细的错误处理,通过 `postError` lambda 报告读取失败位置

### RemoteStrike 的字形摘要机制
`digestFor()` 方法根据 `ActionType`(kPath、kDrawable 或掩码)决定字形的处理方式:
- 首先检查 `fSentGlyphs` 哈希表,若已存在且动作匹配则直接返回
- 否则通过 `SkScalerContext` 创建新字形并加入对应的待发送队列
- 使用 `SkGlyphDigest` 追踪每种动作类型的状态

### 缓存淘汰策略
`checkForDeletedEntries()` 在条目数超过 `fMaxEntriesInDescriptorMap`(默认 2000)时触发:
- 遍历所有远程打击缓存条目
- 检查句柄是否已在客户端删除
- 跳过正在发送中的条目
- 逐步清理直到条目数降至限制以下

### 安全性考虑
- `readStrikeData` 中对缓冲区设置 `setAllowSkSL(false)`,限制字形可绘制对象中的效果类型(crbug.com/1442140)
- volatile 指针用于 `readStrikeData` 参数,防止编译器优化导致的安全问题

## 依赖关系

- **核心依赖**: `SkStrikeCache`, `SkStrikeSpec`, `SkScalerContext`, `SkGlyph`, `SkDescriptor`
- **文本系统**: `sktext::GlyphRun`, `sktext::StrikeForGPU`, `sktext::SkStrikePromise`
- **GPU 文本**: `SubRunContainer`, `SubRunControl`, `TextBlob`, `SubRunAllocator`, `Slug`
- **序列化**: `SkReadBuffer`, `SkWriteBuffer`, `SkFontMetricsPriv`
- **字体系统**: `SkTypeface`, `SkTypefaceProxy`, `SkTypefaceProxyPrototype`
- **内存管理**: `SkArenaAlloc`, `SkArenaAllocWithReset`
- **容器**: `THashTable`, `THashMap`, `THashSet`, `std::unordered_map`

## 设计模式与设计决策

### Pimpl 模式
`SkStrikeServer` 和 `SkStrikeClient` 均使用 Pimpl 模式,将实现隐藏在 `SkStrikeServerImpl` 和 `SkStrikeClientImpl` 中,保持公共 API 的稳定性。

### 策略模式
`DiscardableHandleManager` 接口允许嵌入器(Chromium)自定义缓存条目的生命周期管理策略,服务器端和客户端各有独立的接口定义。

### 延迟初始化
`RemoteStrike` 的 `SkScalerContext` 采用延迟初始化策略:
- `ensureScalerContext()` 仅在需要时创建上下文
- `resetScalerContext()` 在序列化完成后释放上下文以减少内存占用
- `fStrikeSpec` 指针每次调用 `getOrCreateCache` 时更新,支持延迟创建

### 仅计算模式
`GlyphTrackingDevice` 使用 `SubRunContainer::kStrikeCalculationsOnly` 标志,只执行字形度量计算而不产生实际的 SubRun 对象,实现了高效的分析阶段。

### 基于可丢弃句柄的缓存一致性
服务器端通过锁定机制确保数据在传输期间不被客户端删除,客户端通过 `DiscardableStrikePinner` 管理打击缓存的生命周期。

## 性能考量

- **增量传输**: 仅传输新增的字形数据,已发送的字形通过 `fSentGlyphs` 哈希表追踪,避免重复序列化已知字形
- **字体度量优化**: 每个打击的字体度量仅发送一次(`fHaveSentFontMetrics` 标志),后续字形更新不再重传度量数据
- **内存复用**: 使用 `SkArenaAllocWithReset` 管理临时的路径和可绘制对象数据,每次序列化完成后调用 `reset()` 归还内存,减少堆碎片
- **ScalerContext 生命周期**: `resetScalerContext()` 在每次序列化完成后释放 SkScalerContext,该对象可能持有平台字体资源(如 CoreText 或 FreeType 句柄),及时释放减少系统资源占用
- **缓存大小限制**: 默认最多 2000 个条目(`kMaxEntriesInDescriptorMap`),超限时基于可丢弃句柄状态进行懒惰淘汰,仅淘汰客户端已标记删除的条目
- **DFT(距离场文本)支持**: 根据平台设置合理的字体大小阈值,平衡渲染质量和性能:
  - Android: >= 384px 使用路径渲染
  - macOS: >= 256px 使用路径渲染
  - 其他平台: >= 324px 使用路径渲染
  - 所有平台: >= 18px 开始使用距离场渲染(kMinDistanceFieldFontSize)
- **SDF 文本控制**: 通过 `SubRunControl` 参数精细控制何时使用距离场渲染,包括是否支持 DFT、是否使用设备无关字体、是否支持透视 DFT
- **哈希表效率**: `DescToRemoteStrike` 使用 `std::unordered_map` 配合自定义 `MapOps`(基于 `SkDescriptor::getChecksum()` 哈希),提供 O(1) 平均查找时间
- **序列化紧凑性**: 使用 `SkBinaryWriteBuffer` 进行二进制序列化,相比文本格式更紧凑;通过 `snapshotAsData()` 一次性拷贝到输出向量,减少内存分配次数
- **批量处理**: `writeStrikeData` 一次性处理所有待发送的打击和字体原型,减少 IPC 调用次数
- **GlyphTrackingDevice 零开销**: 分析画布使用 `SkNoPixelsDevice` 基类,不分配像素缓冲区;`SubRunContainer::kStrikeCalculationsOnly` 模式不创建实际的 SubRun 对象,仅触发字形度量查询
- **STSubRunAllocator 栈分配**: `GlyphTrackingDevice::onDrawGlyphRunList` 使用 `STSubRunAllocator` 在栈上预分配 SubRunContainer 大小的内存,避免堆分配开销

### 数据流详细分析

完整的远程字形缓存数据流:

1. **分析阶段** (Renderer 进程):
   - 客户端调用 `makeAnalysisCanvas()` 创建分析画布
   - 在画布上执行绘制操作(drawTextBlob、drawSlug 等)
   - `GlyphTrackingDevice` 拦截文本绘制调用
   - `SubRunContainer::MakeInAlloc` 在仅计算模式下运行,触发 `RemoteStrike::digestFor()` 调用
   - 新字形被添加到对应 `RemoteStrike` 的待发送队列中
   - 新字体被添加到 `fTypefacesToSend` 列表

2. **序列化阶段** (Renderer 进程):
   - 调用 `writeStrikeData()` 开始序列化
   - 遍历 `fRemoteStrikesToSend`,统计有待发送字形的打击
   - 无待发送字形的打击立即释放其 ScalerContext
   - 写入字体原型数据(由 `SkTypefaceProxyPrototype::flatten` 处理)
   - 对每个有待发送字形的打击:安装图像/路径/可绘制对象数据,调用 `SkStrike::FlattenGlyphsByType`
   - 清空所有发送队列和 Arena 分配器

3. **传输阶段** (IPC):
   - 序列化后的 `std::vector<uint8_t>` 通过 Chromium 的 IPC 机制传递到 GPU 进程

4. **反序列化阶段** (GPU 进程):
   - 调用 `readStrikeData()` 解析二进制数据
   - 创建 `SkTypefaceProxy` 对象代表远程字体
   - 翻译描述符中的字体 ID(服务器端 -> 客户端)
   - 查找或创建 `SkStrike`,合并新的字形数据
   - 错误处理通过 `postError` lambda 和 `notifyReadFailure` 回调

5. **渲染阶段** (GPU 进程):
   - 使用本地 `SkStrikeCache` 中的字形数据进行实际渲染
   - `DiscardableStrikePinner` 防止正在使用的打击被淘汰

## 相关文件

- `include/private/chromium/SkChromeRemoteGlyphCache.h` - 公共 API 头文件
- `include/private/chromium/Slug.h` - Slug 序列化接口
- `src/core/SkStrike.h` / `src/core/SkStrikeCache.h` - 本地打击缓存
- `src/core/SkTypeface_remote.h` - 远程字体代理
- `src/text/gpu/SubRunContainer.h` - 子运行容器
- `src/text/gpu/SubRunControl.h` - 子运行控制参数
- `src/text/gpu/TextBlob.h` - 文本块管理
- `src/text/StrikeForGPU.h` - GPU 打击接口
- `src/core/SkScalerContext.h` - 字形缩放上下文
- `src/core/SkGlyph.h` - 字形数据结构
- `src/core/SkDescriptor.h` - 描述符和校验和计算
- `src/core/SkFontMetricsPriv.h` - 字体度量序列化工具
- `src/core/SkTraceEvent.h` - 性能追踪事件宏
