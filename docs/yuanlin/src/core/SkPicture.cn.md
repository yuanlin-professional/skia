# SkPicture

> 源文件
> - include/core/SkPicture.h
> - src/core/SkPicture.cpp

## 概述

`SkPicture` 是 Skia 中用于记录和回放绘制命令的抽象类。它可以捕获对 `SkCanvas` 的一系列绘制操作，并在稍后的时间点完整或部分地重新执行这些命令。`SkPicture` 是 Skia 实现延迟渲染、命令缓存和跨进程渲染的核心机制，广泛应用于浏览器渲染引擎（如 Chrome）和移动应用中。该类支持序列化和反序列化，可以将绘制命令保存到文件或内存，并在需要时重建。

## 架构位置

`SkPicture` 位于 Skia 核心渲染架构的记录层：

- 头文件位于 `include/core`，是公开 API 的一部分
- 实现位于 `src/core`，与 `SkPictureRecorder`、`SkPictureData` 等配合工作
- 处于 `SkCanvas` 和底层渲染器之间，提供命令记录和回放能力
- 与 `SkDrawable` 互补，支持嵌套的可绘制对象
- 通过 `SkShader` 接口可以将 Picture 用作着色器

## 主要类与结构体

### SkPicture

绘制命令记录和回放的抽象基类。

**继承关系**

继承自 `SkRefCnt`（引用计数基类）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fUniqueID` | `uint32_t` | Picture 的唯一标识符 |
| `fAddedToCache` | `std::atomic<bool>` | 标识是否已添加到资源缓存 |

**友元类**

- `SkBigPicture`: 大型 Picture 实现
- `SkEmptyPicture`: 空 Picture 实现
- `SkPicturePriv`: 私有辅助类
- `SkPictureData`: Picture 数据存储

### SkPicture::AbortCallback

用于中断 Picture 回放的抽象回调类。

**继承关系**

纯虚基类

**核心方法**

```cpp
virtual bool abort() = 0;
```

在回放过程中定期调用，返回 `true` 时停止回放。

## 公共 API 函数

### 静态工厂函数

#### MakeFromStream

```cpp
static sk_sp<SkPicture> MakeFromStream(SkStream* stream, const SkDeserialProcs* procs = nullptr);
```

从流中反序列化创建 Picture：

- 验证流数据的有效性（magic bytes 和版本号）
- 支持自定义反序列化过程（通过 `procs`）
- 失败时返回 `nullptr`

#### MakeFromData

```cpp
static sk_sp<SkPicture> MakeFromData(const SkData* data, const SkDeserialProcs* procs = nullptr);
static sk_sp<SkPicture> MakeFromData(const void* data, size_t size, const SkDeserialProcs* procs = nullptr);
```

从内存数据反序列化创建 Picture，内部使用 `SkMemoryStream`。

#### MakePlaceholder

```cpp
static sk_sp<SkPicture> MakePlaceholder(SkRect cull);
```

创建占位符 Picture：

- 不执行任何绘制操作
- 仅包含裁剪矩形提示
- 可在回放时被拦截以插入其他命令
- 返回具有唯一标识符的不可变对象

### 序列化函数

#### serialize

```cpp
sk_sp<SkData> serialize(const SkSerialProcs* procs = nullptr) const;
void serialize(SkWStream* stream, const SkSerialProcs* procs = nullptr) const;
```

将 Picture 序列化为数据或写入流：

- 支持自定义序列化过程（通过 `procs`）
- 默认情况下 `SkImage` 被编码为 `nullptr`
- 需要提供 `fImageProc` 才能正确序列化图像（如编码为 PNG）

### 回放函数

#### playback

```cpp
virtual void playback(SkCanvas* canvas, AbortCallback* callback = nullptr) const = 0;
```

在指定的 Canvas 上回放绘制命令：

- 每个命令单独发送到 Canvas
- 可选的 `AbortCallback` 允许中断回放
- 中断时 Canvas 的状态栈会被恢复

### 属性访问

#### cullRect

```cpp
virtual SkRect cullRect() const = 0;
```

返回创建 Picture 时传入的裁剪矩形提示（不是精确边界）。

#### uniqueID

```cpp
uint32_t uniqueID() const;
```

返回 Picture 的唯一标识符，在进程内唯一。

#### approximateOpCount

```cpp
virtual int approximateOpCount(bool nested = false) const = 0;
```

返回 Picture 中的近似操作数：

- `nested = true` 时包含嵌套 Picture 的操作数
- 返回值可能大于或小于实际 Canvas 调用次数（由于优化）

#### approximateBytesUsed

```cpp
virtual size_t approximateBytesUsed() const = 0;
```

返回 Picture 占用的近似字节数（不包括大对象引用）。

### 着色器创建

#### makeShader

```cpp
sk_sp<SkShader> makeShader(SkTileMode tmx, SkTileMode tmy, SkFilterMode mode,
                           const SkMatrix* localMatrix, const SkRect* tileRect) const;
sk_sp<SkShader> makeShader(SkTileMode tmx, SkTileMode tmy, SkFilterMode mode) const;
```

创建使用 Picture 绘制的着色器：

- 支持平铺模式（X 和 Y 方向）
- 支持过滤模式
- 可选的局部变换矩阵
- 可选的平铺矩形（子集或超集）

## 内部实现细节

### 序列化格式

Picture 序列化使用以下结构：

**Magic Bytes**

```cpp
static const char kMagic[] = { 's', 'k', 'i', 'a', 'p', 'i', 'c', 't' };
```

所有 Picture 序列化数据以这8个字节开始。

**版本控制**

```cpp
enum SerializationVersions {
    kJustPublicData_Version = 4,            // 2018年2月引入
    kVerbsAreStoredForward_Version = 5,     // 2019年9月引入
    kMin_Version     = kJustPublicData_Version,
    kCurrent_Version = kVerbsAreStoredForward_Version
};
```

支持版本4及以上，当前版本为5。

**Packed Header**

```cpp
int32_t packed = (static_cast<int>(fFillType) << kFillType_SerializationShift) |
                 ((int)firstDir << kDirection_SerializationShift) |
                 (SerializationType::kRRect << kType_SerializationShift) |
                 kCurrent_Version;
```

头部使用位字段编码版本、填充类型、方向等信息。

**Trailing Byte**

序列化头部后紧跟一个标识字节：

- `kFailure_TrailingStreamByteAfterPictInfo (0)`: 失败，无数据
- `kPictureData_TrailingStreamByteAfterPictInfo (1)`: 标准 Picture 数据
- `kCustom_TrailingStreamByteAfterPictInfo (2)`: 自定义格式，后跟负数大小

### 唯一 ID 生成

使用原子操作生成全局唯一 ID：

```cpp
SkPicture::SkPicture() {
    static std::atomic<uint32_t> nextID{1};
    do {
        fUniqueID = nextID.fetch_add(+1, std::memory_order_relaxed);
    } while (fUniqueID == 0);
}
```

跳过 ID 0，确保所有有效 Picture 都有非零 ID。

### 前向移植（Forwardport）

`Forwardport` 函数将旧格式的 Picture 转换为当前格式：

```cpp
sk_sp<SkPicture> SkPicture::Forwardport(const SkPictInfo& info,
                                        const SkPictureData* data,
                                        SkReadBuffer* buffer) {
    SkPicturePlayback playback(data);
    SkPictureRecorder r;
    playback.draw(r.beginRecording(info.fCullRect), nullptr, buffer);
    return r.finishRecordingAsPicture();
}
```

通过回放旧 Picture 并重新记录实现版本升级。

### 后向移植（Backport）

`backport` 函数将当前 Picture 转换为可序列化的 `SkPictureData`：

```cpp
SkPictureData* SkPicture::backport() const {
    SkPictInfo info = this->createHeader();
    SkPictureRecord rec(info.fCullRect.roundOut(), 0);
    rec.beginRecording();
        this->playback(&rec);
    rec.endRecording();
    return new SkPictureData(rec, info);
}
```

通过回放当前 Picture 到 `SkPictureRecord` 实现。

### 自定义序列化

支持通过 `SkSerialProcs` 提供自定义序列化：

```cpp
static sk_sp<const SkData> custom_serialize(const SkPicture* picture, const SkSerialProcs& procs) {
    if (procs.fPictureProc) {
        auto data = procs.fPictureProc(const_cast<SkPicture*>(picture), procs.fPictureCtx);
        if (data) {
            return data;
        }
    }
    return nullptr;
}
```

如果提供了 `fPictureProc`，优先使用自定义序列化。

### 嵌套限制

为防止无限递归，反序列化时使用递归深度限制：

```cpp
static const int kNestedSKPLimit = 100;
```

超过限制时返回 `nullptr`。

### 占位符实现

`MakePlaceholder` 创建一个内部 `Placeholder` 类：

```cpp
struct Placeholder : public SkPicture {
    explicit Placeholder(SkRect cull) : fCull(cull) {}
    void playback(SkCanvas*, AbortCallback*) const override { }
    int approximateOpCount(bool) const override {
        return kMaxPictureOpsToUnrollInsteadOfRef+1;
    }
    size_t approximateBytesUsed() const override { return sizeof(*this); }
    SkRect cullRect() const override { return fCull; }
    SkRect fCull;
};
```

操作数设置为超过展开阈值，避免被展开到父 Picture 中。

### 资源缓存集成

析构函数中通知资源缓存：

```cpp
SkPicture::~SkPicture() {
    if (fAddedToCache.load()) {
        SkResourceCache::PostPurgeSharedID(SkPicturePriv::MakeSharedID(fUniqueID));
    }
}
```

确保缓存中相关资源被清理。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkCanvas` | 回放目标，接收绘制命令 |
| `SkData` | 序列化数据存储 |
| `SkStream` | 流式序列化和反序列化 |
| `SkPictureRecorder` | 创建 Picture 的记录器 |
| `SkPictureData` | Picture 数据存储和管理 |
| `SkPicturePlayback` | 回放引擎 |
| `SkPictureRecord` | 记录引擎 |
| `SkSerialProcs`/`SkDeserialProcs` | 自定义序列化过程 |
| `SkResourceCache` | 资源缓存系统 |
| `SkShader` | 着色器接口 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| `SkPictureRecorder` | 创建和记录 Picture |
| `SkCanvas` | 通过 `drawPicture` 绘制 Picture |
| `SkDrawable` | 可包含 Picture 作为可绘制对象 |
| Chrome 渲染引擎 | 使用 Picture 进行跨进程渲染 |
| Android Framework | 使用 Picture 缓存绘制命令 |

## 设计模式与设计决策

### 抽象工厂模式

`SkPicture` 是抽象基类：

- 具体实现包括 `SkBigPicture`（标准实现）和 `SkEmptyPicture`（空实现）
- 通过静态工厂方法（`MakeFromStream`、`MakePlaceholder` 等）创建
- 隐藏具体实现细节

### 命令模式

Picture 本质上是命令模式的实现：

- 记录一系列绘制命令
- 延迟执行，可以多次回放
- 支持命令的序列化和传输

### 策略模式

通过 `SkSerialProcs` 和 `SkDeserialProcs` 实现策略模式：

- 允许自定义序列化和反序列化行为
- 支持不同的图像编码策略
- 支持自定义 Picture 格式

### 观察者模式

`AbortCallback` 实现观察者模式：

- 回放过程中定期查询回调
- 允许外部控制回放流程
- 支持中断和条件停止

### 引用计数

继承 `SkRefCnt` 使用智能指针管理生命周期：

- 自动内存管理
- 支持跨模块共享
- 线程安全的引用计数

### 版本兼容性

支持向前和向后兼容：

- `Forwardport`: 将旧版本升级到新版本
- `Backport`: 将新版本转换为可序列化格式
- 版本检查和拒绝不支持的版本

### 占位符模式

`MakePlaceholder` 提供占位符实现：

- 可在回放时被拦截
- 支持延迟加载和动态替换
- 用于跨进程渲染场景

## 性能考量

### 命令缓存

Picture 的核心性能优势：

- 记录一次，多次回放
- 避免重复计算和命令生成
- 适合静态或半静态内容

### 序列化开销

序列化和反序列化有一定开销：

- `backport` 需要完整回放 Picture
- 自定义序列化可以优化特定场景
- 序列化数据可以跨进程传输

### 嵌套深度限制

防止深度嵌套导致的性能问题：

- 限制递归深度为 100
- 避免栈溢出
- 防止恶意或错误的数据

### 操作数阈值

控制 Picture 展开行为：

- 小 Picture 可以展开到父 Picture
- 大 Picture 保持独立，避免过度展开
- 占位符使用较大的操作数避免展开

### 资源缓存

通过 `fAddedToCache` 集成资源缓存系统：

- 避免重复加载相同的 Picture
- 自动清理未使用的资源
- 提高内存利用效率

### 原子操作

唯一 ID 生成使用 `memory_order_relaxed`：

- 避免不必要的内存屏障
- 在高并发场景下提高性能
- ID 唯一性不需要严格的顺序保证

### 适用场景

最佳使用场景：

- 需要多次重绘的静态或半静态内容
- 跨进程渲染（如 Chrome 的 GPU 进程）
- 延迟渲染和命令缓存
- 绘制命令的序列化和传输

### 性能权衡

- **优势**：命令缓存，多次回放，跨进程传输
- **劣势**：记录和序列化有开销，内存占用
- **权衡**：适合重复渲染，不适合一次性绘制

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/core/SkPictureRecorder.h` | Picture 记录器 |
| `src/core/SkPictureData.h/.cpp` | Picture 数据存储 |
| `src/core/SkPicturePlayback.h/.cpp` | 回放引擎 |
| `src/core/SkPictureRecord.h/.cpp` | 记录引擎 |
| `src/core/SkPicturePriv.h` | 私有辅助函数 |
| `include/core/SkCanvas.h` | 回放目标和记录源 |
| `include/core/SkSerialProcs.h` | 序列化过程定义 |
| `src/core/SkResourceCache.h` | 资源缓存系统 |
| `include/core/SkDrawable.h` | 可绘制对象接口 |
| `include/core/SkShader.h` | 着色器基类 |
