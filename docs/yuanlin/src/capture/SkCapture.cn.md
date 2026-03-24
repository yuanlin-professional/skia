# SkCapture

> 源文件: src/capture/SkCapture.h, src/capture/SkCapture.cpp

## 概述

`SkCapture` 是 Skia 图形库中用于捕获和序列化绘图操作的核心类。该类提供了将多个 `SkPicture` 对象打包成一个可序列化数据块的能力，同时支持从序列化数据中恢复这些图片对象。它是 Skia 捕获系统的基础组件，允许开发者记录、存储和重放绘图命令。

`SkCapture` 继承自 `SkRefCnt`，使用引用计数进行内存管理。该类目前处于活跃开发阶段（版本号为 0），API 可能会发生变化。主要用于将画布上的绘图操作序列化为持久化格式，以便后续分析、调试或重放。

## 架构位置

`SkCapture` 位于 Skia 的捕获子系统中，属于 `src/capture` 模块。在整个架构中，它扮演以下角色：

- **上层依赖**: 被 `SkCaptureManager` 使用，负责管理捕获会话
- **协作类**: 与 `SkCaptureCanvas` 配合工作，后者负责拦截和记录绘图命令
- **核心依赖**: 依赖于 `SkPicture`（记录绘图命令）、`SkData`（数据存储）和 `SkSerialProcs`（自定义序列化）
- **应用场景**: 用于性能分析、渲染调试、自动化测试等需要记录和重放绘图操作的场景

捕获系统的数据流向：`SkCanvas` → `SkCaptureCanvas` → `SkPicture` → `SkCapture` → 序列化数据

## 主要类与结构体

### SkCapture 类

**继承关系**: 继承自 `SkRefCnt`，支持智能指针 `sk_sp<SkCapture>` 管理生命周期。

**主要成员变量**:
- `Metadata fMetadata`: 元数据结构，包含版本号和图片数量
- `skia_private::TArray<sk_sp<SkPicture>> fPictures`: 存储所有捕获的图片对象
- `static const uint32_t kVersion`: 当前格式版本号（版本 0）

### Metadata 结构体

```cpp
struct Metadata {
    uint32_t version;       // 序列化格式版本
    uint32_t numPictures;   // 图片数量
};
```

用于描述捕获数据的基本信息，在序列化和反序列化时进行版本校验。

## 公共 API 函数

### 工厂方法

**MakeFromData**
```cpp
static sk_sp<SkCapture> MakeFromData(sk_sp<const SkData>)
```
从序列化数据创建 `SkCapture` 对象。执行以下步骤：
1. 读取并验证魔数（'skia' + 'capt'）
2. 检查版本号兼容性
3. 读取图片数量
4. 逐个反序列化 `SkPicture` 对象
5. 返回构造完成的 `SkCapture` 实例

如果任何步骤失败（魔数错误、版本不匹配、数据损坏等），返回 `nullptr`。

**MakeFromPictures**
```cpp
static sk_sp<SkCapture> MakeFromPictures(skia_private::TArray<sk_sp<SkPicture>>)
```
从图片数组创建 `SkCapture` 对象。直接将传入的图片集合封装为捕获对象，设置元数据中的版本号和图片数量。

### 序列化方法

**serializeCapture**
```cpp
sk_sp<SkData> serializeCapture()
```
将整个捕获对象序列化为二进制数据。序列化格式：
```
[魔数1: 4字节] [魔数2: 4字节] [版本: 4字节] [图片数量: 4字节]
[图片1大小: 4字节] [图片1数据: N字节]
[图片2大小: 4字节] [图片2数据: N字节]
...
```

使用自定义的 `serializeImageProc` 处理图片序列化。

### 访问方法

**getPicture**
```cpp
sk_sp<SkPicture> getPicture(int i) const
```
根据索引获取指定图片。索引超出范围返回 `nullptr`。

**getMetadata**
```cpp
Metadata getMetadata() const
```
获取捕获对象的元数据（版本和图片数量）。

## 内部实现细节

### 魔数验证

使用双魔数机制提高文件格式识别可靠性：
- `kMagic1 = SkSetFourByteTag('s','k','i','a')`: 标识 Skia 格式
- `kMagic2 = SkSetFourByteTag('c','a','p','t')`: 标识捕获格式

### 图片序列化流程

在 `serializeCapture` 中，每个 `SkPicture` 被单独序列化：
1. 创建临时内存流 `SkDynamicMemoryWStream`
2. 使用 `SkSerialProcs` 配置自定义序列化回调
3. 调用 `picture->serialize()` 将图片写入流
4. 将序列化大小和数据写入主流

### 自定义图片处理（待实现）

**serializeImageProc**: 当 `SkPicture` 中包含图片（通过 `drawImage` 等绘制）时调用。当前实现只返回占位符 `contentID = -1`。未来计划：
- 识别来自 `SkSurface` 的内容图片
- 使用 `contentID` 关联到对应的 `SkPicture`
- 避免重复编码，减少数据冗余

**deserializeImageProc**: 反序列化时重建图片。当前返回 5x5 洋红色占位图片。未来将根据 `contentID` 查找并返回正确的图片引用。

### 错误处理

反序列化过程中的每个步骤都有错误检测：
- 使用 `SkDebugf` 输出详细错误信息
- 任何失败立即返回 `nullptr`
- 验证内存分配成功（检查 `SkData::MakeUninitialized` 返回值）
- 检查流读取的字节数是否匹配预期

## 依赖关系

### 直接依赖
- **SkPicture**: 存储和序列化绘图命令
- **SkData**: 管理二进制数据的生命周期
- **SkSerialProcs**: 提供序列化/反序列化的自定义钩子
- **SkStream**: 内存流读写操作
- **SkTArray**: 高效的动态数组容器

### 被依赖
- **SkCaptureManager**: 管理捕获会话，创建和组织 `SkCapture` 对象
- **SkCaptureCanvas**: 记录绘图操作并生成 `SkPicture`

### 间接依赖
- **SkCanvas**: 通过 `SkCaptureCanvas` 间接依赖
- **SkImage/SkBitmap**: 用于图片占位符生成

## 设计模式与设计决策

### 工厂模式
使用静态工厂方法（`MakeFromData` 和 `MakeFromPictures`）而非公共构造函数，优点：
- 可以返回 `nullptr` 表示创建失败
- 与 Skia 的智能指针 `sk_sp` 配合良好
- 封装复杂的初始化逻辑

### 策略模式
通过 `SkSerialProcs` 允许自定义序列化策略：
- `fImageProc`: 序列化图片时的自定义处理
- `fImageDataProc`: 反序列化图片时的自定义处理
- 为未来扩展留下接口（如自定义字体、路径序列化）

### 版本控制策略
使用显式版本号 `kVersion = 0` 标识格式处于开发阶段：
- 读取时严格检查版本匹配
- 版本不兼容时立即拒绝加载
- 为未来格式演进提供基础

### 待优化的设计

当前代码中多处 TODO 注释表明设计仍在演化：
1. **索引访问问题**: `getPicture(int i)` 缺乏组织结构，计划改为按 Surface 和 Recording 分组
2. **图片所有权**: `fPictures` 应移至 `SkCaptureManager` 统一管理
3. **元数据缺失**: `SkPicture` 缺少关联的画布信息和绘制关系
4. **图片引用**: 需要实现 `contentID` 机制避免图片重复编码

## 性能考量

### 内存管理
- 使用 `sk_sp` 引用计数，避免手动内存管理
- `TArray` 预分配策略减少动态分配次数
- 序列化时使用 `SkDynamicMemoryWStream` 避免多次内存拷贝

### 序列化效率
- **优势**: 分块写入，每个图片独立序列化便于增量处理
- **劣势**: 当前图片序列化使用临时流，存在额外拷贝开销
- **待优化**: 图片内容 ID 机制可大幅减少重复图片编码

### 反序列化安全性
- 先读取大小再分配内存，避免恶意数据导致的过度分配
- 逐步验证数据完整性，出错快速失败
- 使用 `SkData::MakeUninitialized` 减少初始化开销

### 可扩展性
- 当前版本 0 不保证向后兼容，允许快速迭代
- 预留版本号字段，未来可实现格式升级
- `SkSerialProcs` 机制支持自定义序列化逻辑

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/capture/SkCaptureManager.h` | 协作 | 管理捕获会话，创建 SkCapture 对象 |
| `src/capture/SkCaptureCanvas.h` | 协作 | 拦截绘图命令，生成 SkPicture |
| `include/core/SkPicture.h` | 依赖 | 记录和重放绘图命令 |
| `include/core/SkData.h` | 依赖 | 管理二进制数据 |
| `include/core/SkSerialProcs.h` | 依赖 | 提供序列化自定义钩子 |
| `include/core/SkStream.h` | 依赖 | 内存流读写操作 |
| `include/core/SkImage.h` | 依赖 | 图片对象（用于占位符） |
| `include/private/base/SkTArray.h` | 依赖 | 动态数组容器 |
