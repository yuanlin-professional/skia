# Slug — GPU 文本渲染 Slug 实现

> 源文件: `src/text/gpu/Slug.cpp`

## 概述

`Slug.cpp` 实现了 Skia GPU 文本渲染系统中 `Slug` 类的核心操作方法。`Slug`（字面意思为"铅条"，源自印刷术语）是 Skia 为 GPU 文本渲染优化而设计的预处理文本对象。

Slug 的工作流程是：
1. **创建**: 将 `SkTextBlob`（文本的高级表示）转换为 Slug，完成字形查找、定位等计算
2. **序列化/反序列化**: 支持跨进程传输（特别是 Chromium 的渲染进程架构）
3. **绘制**: 在 `SkCanvas` 上高效绘制，跳过文本处理步骤

该文件实现了创建、序列化、反序列化和绘制这四个核心操作。

## 架构位置

```
Skia
├── include/private/chromium/
│   └── Slug.h                    // Slug 类声明（Chromium 私有 API）
├── src/text/
│   ├── SlugFromBuffer.cpp        // 反序列化入口和 ID 生成
│   └── gpu/
│       └── Slug.cpp              // 本文件：核心操作实现
├── src/core/
│   ├── SkReadBuffer.h            // 序列化读取
│   └── SkWriteBuffer.h           // 序列化写入
```

`Slug` 是 Chromium 的私有 API（位于 `include/private/chromium/`），主要为 Chromium 的 GPU 进程文本渲染管线提供服务。

## 主要类与结构体

### `Slug`（`sktext::gpu` 命名空间）

Slug 是文本绘制的预处理单元，核心功能在本文件中实现。该类继承自引用计数基类 `SkRefCnt`。

## 公共 API 函数

### `sk_sp<Slug> Slug::ConvertBlob(SkCanvas* canvas, const SkTextBlob& blob, SkPoint origin, const SkPaint& paint)`

- **功能**: 将 `SkTextBlob` 转换为 `Slug`
- **参数**:
  - `canvas`: 目标画布（提供设备和字体缓存上下文）
  - `blob`: 源文本 blob
  - `origin`: 文本绘制原点
  - `paint`: 绘制属性（颜色、抗锯齿等）
- **实现**: 委托给 `canvas->convertBlobToSlug()`

### `sk_sp<SkData> Slug::serialize() const`

- **功能**: 将 Slug 序列化为二进制数据
- **返回值**: 包含序列化数据的 `SkData`
- **实现**: 使用 `SkBinaryWriteBuffer` 写入，调用虚函数 `doFlatten()` 执行序列化

### `size_t Slug::serialize(void* buffer, size_t size) const`

- **功能**: 将 Slug 序列化到预分配的缓冲区
- **参数**:
  - `buffer`: 预分配的缓冲区
  - `size`: 缓冲区大小
- **返回值**: 实际写入的字节数；如果缓冲区不够大返回 0
- **溢出检测**: 通过 `writeBuffer.usingInitialStorage()` 检查是否发生了内部缓冲区重新分配

### `sk_sp<Slug> Slug::Deserialize(const void* data, size_t size, const SkStrikeClient* client)`

- **功能**: 从二进制数据反序列化 Slug
- **参数**:
  - `data`: 序列化数据
  - `size`: 数据大小
  - `client`: 字体打击缓存客户端（用于解析字体引用）
- **实现**: 设置反序列化回调后调用 `MakeFromBuffer()`

### `void Slug::draw(SkCanvas* canvas, const SkPaint& paint) const`

- **功能**: 在画布上绘制 Slug
- **实现**: 委托给 `canvas->drawSlug()`

## 内部实现细节

### 序列化机制

序列化使用 Skia 标准的 `SkBinaryWriteBuffer` 框架：
1. 创建写入缓冲区
2. 调用虚函数 `doFlatten()` 将 Slug 数据写入
3. 通过 `snapshotAsData()` 获取序列化数据

带缓冲区的 `serialize(void*, size_t)` 重载使用了与 `SkTextBlob` 相同的缓冲区溢出检测惯用法：
- `SkWriteBuffer` 在缓冲区不够时会自动分配新缓冲区
- 通过 `usingInitialStorage()` 判断是否仍在使用初始传入的缓冲区
- 如果不是，说明发生了溢出，返回 0

### 反序列化流程

```
Deserialize() -> 设置 SkDeserialProcs -> MakeFromBuffer() -> procs.fSlugProc()
```

`AddDeserialProcs` 将 Slug 的反序列化回调注册到 `SkDeserialProcs` 中，`MakeFromBuffer`（在 `SlugFromBuffer.cpp` 中实现）调用该回调完成实际反序列化。

### Canvas 委托

创建 (`ConvertBlob`) 和绘制 (`draw`) 操作都委托给 `SkCanvas`。这是因为 Canvas 持有设备上下文和字体缓存等必要资源。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `Slug.h` | Slug 类声明 |
| `SkCanvas.h` | 画布（转换和绘制入口） |
| `SkPoint.h` | 文本原点坐标 |
| `SkSerialProcs.h` | 序列化/反序列化回调 |
| `SkReadBuffer.h` | 反序列化读取 |
| `SkWriteBuffer.h` | 序列化写入 |

## 设计模式与设计决策

1. **代理模式**: `ConvertBlob` 和 `draw` 委托给 Canvas，Slug 本身不直接访问 GPU 资源
2. **二进制序列化**: 使用 Skia 标准的 `SkBinaryWriteBuffer`/`SkReadBuffer` 框架，与其他 Skia 对象（如 `SkTextBlob`、`SkPicture`）共享序列化基础设施
3. **溢出安全**: 固定缓冲区序列化使用 `usingInitialStorage()` 惯用法检测溢出，与 `SkTextBlob` 保持一致
4. **Chromium 集成**: Slug 作为 Chromium 的私有 API 设计，支持通过 `SkStrikeClient` 进行跨进程字体解析
5. **关注点分离**: 序列化/反序列化的框架逻辑与具体数据格式（`doFlatten` 虚函数）分离

## 性能考量

- Slug 的主要性能优势在于将文本处理结果缓存，后续帧直接绘制而无需重新处理
- 序列化/反序列化使用二进制格式，比文本格式更高效
- `serialize(void*, size_t)` 允许使用预分配缓冲区，避免堆分配
- `draw()` 直接绘制预处理数据，跳过了字形查找和文本布局

## 相关文件

- `include/private/chromium/Slug.h` — Slug 类声明
- `src/text/SlugFromBuffer.cpp` — `MakeFromBuffer` 和 `NextUniqueID`
- `include/core/SkCanvas.h` — Canvas（`convertBlobToSlug`、`drawSlug`）
- `include/core/SkTextBlob.h` — 文本 blob（Slug 的输入源）
- `include/core/SkSerialProcs.h` — 序列化回调定义
- `src/core/SkReadBuffer.h` / `src/core/SkWriteBuffer.h` — 序列化基础设施
