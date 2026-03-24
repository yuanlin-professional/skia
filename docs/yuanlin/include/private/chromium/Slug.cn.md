# Slug

> 源文件: `include/private/chromium/Slug.h`

## 概述
Slug 是一个封装了特定原点和绘制属性的 SkTextBlob 对象,可以看作是将文本块制作成"橡皮图章"。它支持通过画布的矩阵和裁剪变换进行操作,当画布变换时,Slug 也会随之变换,较小的字形使用双线性插值渲染。Slug 是 Skia 文本渲染系统中用于优化文本绘制性能的高级抽象。

## 架构位置
该文件位于 Skia 的 Chromium 私有接口层,属于 sktext::gpu 命名空间,是 GPU 文本渲染子系统的一部分。Slug 位于 SkTextBlob 和最终 GPU 渲染之间,提供了可序列化、可变换的文本渲染表示,主要用于 Chromium 的文本渲染管线。

## 主要类与结构体

### Slug
文本渲染的"橡皮图章"表示,封装了文本、位置和绘制属性。

**继承关系**: SkRefCnt → Slug

**关键特性**:
- 可序列化和反序列化
- 支持画布变换
- 优化的 GPU 渲染路径
- 双线性插值的字形缩放

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fUniqueID | const uint32_t | 唯一标识符,通过 NextUniqueID() 生成 |

## 公共 API 函数

### 创建与转换

#### `static sk_sp<Slug> ConvertBlob(SkCanvas* canvas, const SkTextBlob& blob, SkPoint origin, const SkPaint& paint)`
- **功能**: 从 SkTextBlob 创建 Slug 对象
- **参数**:
  - `canvas`: 目标画布,捕获当前的变换和绘制上下文
  - `blob`: 源文本 blob,包含字形和位置信息
  - `origin`: 文本绘制的原点坐标
  - `paint`: 绘制属性(颜色、字体、抗锯齿等)
- **返回值**: 成功返回 Slug 对象,如果由于绘制优化(非裁剪原因)不会绘制则返回 nullptr
- **用途**: 类似 drawTextBlob 的捕获过程

### 序列化

#### `sk_sp<SkData> serialize() const`
- **功能**: 将 Slug 序列化为数据块
- **参数**: 无
- **返回值**: 包含序列化数据的 SkData 对象
- **用途**: 保存 Slug 用于缓存或跨进程传输

#### `size_t serialize(void* buffer, size_t size) const`
- **功能**: 将 Slug 序列化到指定的缓冲区
- **参数**:
  - `buffer`: 目标缓冲区指针
  - `size`: 缓冲区大小
- **返回值**: 实际写入的字节数
- **用途**: 避免额外的内存分配

### 反序列化

#### `static sk_sp<Slug> Deserialize(const void* data, size_t size, const SkStrikeClient* client = nullptr)`
- **功能**: 从序列化数据重建 Slug 对象
- **参数**:
  - `data`: 序列化数据的指针
  - `size`: 数据大小
  - `client`: 可选的 SkStrikeClient,用于字体 ID 转换
- **返回值**: 成功返回 Slug 对象,失败返回 nullptr
- **用途**: 从缓存或远程数据恢复 Slug

#### `static sk_sp<Slug> MakeFromBuffer(SkReadBuffer& buffer)`
- **功能**: 从 SkReadBuffer 读取 Slug
- **参数**: `buffer` - 读取缓冲区
- **返回值**: 成功返回 Slug 对象,失败返回 nullptr
- **用途**: 与 Skia 的序列化框架集成

#### `static void AddDeserialProcs(SkDeserialProcs* procs, const SkStrikeClient* client = nullptr)`
- **功能**: 添加 Slug 的反序列化处理器到 SkDeserialProcs
- **参数**:
  - `procs`: 反序列化处理器集合
  - `client`: 可选的字体客户端
- **返回值**: 无
- **用途**: 允许客户端反序列化包含 Slug 数据的 SkPicture

### 绘制

#### `void draw(SkCanvas* canvas, const SkPaint& paint) const`
- **功能**: 在画布上绘制 Slug
- **参数**:
  - `canvas`: 目标画布,遵循其变换和裁剪
  - `paint`: 可选的额外绘制属性(可能覆盖创建时的属性)
- **返回值**: 无

### 边界查询

#### `virtual SkRect sourceBounds() const = 0`
- **功能**: 获取源空间的边界矩形(不含原点偏移)
- **参数**: 无
- **返回值**: 文本的边界矩形
- **用途**: 裁剪测试、布局计算

#### `virtual SkRect sourceBoundsWithOrigin() const = 0`
- **功能**: 获取包含原点偏移的源空间边界
- **参数**: 无
- **返回值**: 包含原点的边界矩形
- **用途**: 完整的空间占用查询

### 其他

#### `uint32_t uniqueID() const`
- **功能**: 获取 Slug 的唯一标识符
- **参数**: 无
- **返回值**: 唯一的 32 位 ID

#### `virtual void doFlatten(SkWriteBuffer&) const = 0`
- **功能**: 将 Slug 扁平化到写缓冲区(子类实现)
- **参数**: `SkWriteBuffer` - 写缓冲区
- **返回值**: 无
- **用途**: 序列化框架的内部接口

## 内部实现细节

### Slug 的生命周期
```
SkTextBlob + SkPaint + origin
         ↓
   ConvertBlob()
         ↓
      Slug (缓存)
         ↓
    serialize()
         ↓
   序列化数据(可持久化)
         ↓
   Deserialize()
         ↓
      Slug
         ↓
     draw()
         ↓
   GPU 渲染
```

### 唯一 ID 生成
```cpp
static uint32_t NextUniqueID();
const uint32_t fUniqueID{NextUniqueID()};
```
每个 Slug 实例有唯一 ID,用于:
- 缓存键
- 调试追踪
- 资源管理

### 字体 ID 转换
SkStrikeClient 参数用于跨进程场景:
- 渲染进程有自己的字体 ID 空间
- GPU 进程有不同的字体 ID 空间
- SkStrikeClient 负责 ID 映射

### 双线性插值缩放
当 Slug 被变换(缩放/旋转)时:
- 小字形使用双线性插值
- 保持平滑的视觉效果
- 避免重新生成字形纹理

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRect | 边界矩形 |
| SkRefCnt | 引用计数基类 |
| SkAPI | API 导出宏 |
| SkCanvas | 绘制目标 |
| SkData | 序列化数据容器 |
| SkPaint | 绘制属性 |
| SkTextBlob | 源文本数据 |
| SkReadBuffer/SkWriteBuffer | 序列化框架 |
| SkStrikeClient | 字体远程化支持 |
| SkDeserialProcs | 反序列化处理器 |

### 被依赖的模块
- Chromium 的文本渲染管线
- Blink 渲染引擎的文本绘制
- Skia GPU 文本渲染后端
- SkPicture(通过 DeserialProcs 集成)
- 文本缓存系统

## 设计模式与设计决策

### 快照模式
Slug 捕获文本的快照:
- 包含文本内容、位置、属性
- 与源 TextBlob 解耦
- 可以独立变换和绘制

### 享元模式的应用
Slug 可能共享底层的字形纹理:
- 多个 Slug 可能引用相同的字形
- 减少 GPU 内存占用
- 提高缓存命中率

### 序列化支持
完整的序列化/反序列化能力:
- 支持跨进程使用(Chromium 多进程架构)
- 可以缓存到磁盘
- 与 SkPicture 集成

### 不可变性
Slug 创建后不可修改:
- 线程安全的读取
- 可以安全地缓存
- 简化并发管理

### 橡皮图章比喻
Slug 像橡皮图章:
- 制作一次(ConvertBlob)
- 多次使用(draw)
- 可以在不同位置、大小使用
- 保持相对形状

## 性能考量

### 创建开销
ConvertBlob() 有一定开销:
- 字形查找和布局
- GPU 资源准备
- 应该缓存 Slug 而非每帧创建

### 绘制优化
使用 Slug 绘制比重复 drawTextBlob 高效:
- 避免重复的字形查找
- 重用字形纹理
- 优化的 GPU 命令

### 序列化成本
序列化和反序列化有开销:
- 适合跨进程或持久化场景
- 不适合每帧序列化
- 序列化格式紧凑

### 变换处理
Slug 支持高效的变换:
- 双线性插值的字形缩放
- 无需重新生成字形
- GPU 上的变换操作

### 缓存友好
Slug 设计为缓存友好:
- 不可变性支持长期缓存
- 唯一 ID 作为缓存键
- 序列化支持持久缓存

## 使用场景

### Chromium 文本渲染
典型的使用流程:
```cpp
// 在合成线程
auto slug = sktext::gpu::Slug::ConvertBlob(
    canvas, textBlob, origin, paint);

// 序列化传递给 GPU 进程
auto data = slug->serialize();
sendToGPUProcess(data);

// GPU 进程反序列化
auto slug = sktext::gpu::Slug::Deserialize(
    data->data(), data->size(), strikeClient);

// 绘制
slug->draw(gpuCanvas, paint);
```

### 文本缓存
缓存常用文本:
```cpp
uint32_t cacheKey = slug->uniqueID();
if (!cache->contains(cacheKey)) {
    cache->insert(cacheKey, slug);
}
auto cachedSlug = cache->get(cacheKey);
cachedSlug->draw(canvas, paint);
```

### SkPicture 集成
在 Picture 中使用 Slug:
```cpp
SkDeserialProcs procs;
sktext::gpu::Slug::AddDeserialProcs(&procs, strikeClient);
auto picture = SkPicture::MakeFromData(data, &procs);
```

## 平台相关说明

### GPU 后端支持
Slug 依赖 GPU 渲染:
- 主要用于 Ganesh 后端
- 可能支持 Graphite 后端
- CPU 后端可能降级到传统 TextBlob

### Chromium 多进程架构
特别为 Chromium 优化:
- 渲染进程创建 Slug
- 序列化传递给 GPU 进程
- GPU 进程反序列化并绘制
- SkStrikeClient 处理字体远程化

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkTextBlob.h | 源文本数据 |
| include/core/SkCanvas.h | 绘制目标 |
| include/core/SkPaint.h | 绘制属性 |
| src/text/gpu/SlugImpl.h | Slug 的实现类 |
| src/text/gpu/TextBlobRedrawCoordinator.h | 文本重绘协调器 |
| include/private/chromium/SkStrikeClient.h | 字体远程化客户端 |
| include/core/SkPicture.h | 与 Picture 集成 |
| src/gpu/ganesh/GrAtlasTextOp.h | GPU 文本渲染操作 |
