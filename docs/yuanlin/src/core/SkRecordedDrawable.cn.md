# SkRecordedDrawable

> 源文件: src/core/SkRecordedDrawable.h, src/core/SkRecordedDrawable.cpp

## 概述

`SkRecordedDrawable` 是一个将录制的绘图命令序列封装为可复用的 `SkDrawable` 对象的类。它持有 `SkRecord` 录制数据、可选的边界盒层次结构(BBH)和可绘制对象列表,可以在多个上下文中重放这些命令,或将其转换为 `SkPicture` 对象。该类是 Skia 绘图录制与回放机制的重要组成部分。

## 架构位置

`SkRecordedDrawable` 位于 Skia 核心绘图引擎的录制层,处于以下位置:
- 继承自 `SkDrawable`,属于可绘制对象体系
- 与 `SkRecord`、`SkRecordCanvas` 协同工作,形成完整的录制-回放流程
- 作为 `SkPictureRecorder` 的输出形式之一
- 连接 `SkRecord` 底层存储和 `SkPicture` 高层抽象

## 主要类与结构体

### SkRecordedDrawable

**继承关系:**
```
SkDrawable (include/core/SkDrawable.h)
  └── SkRecordedDrawable
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRecord` | `sk_sp<SkRecord>` | 存储录制的绘图命令序列 |
| `fBBH` | `sk_sp<SkBBoxHierarchy>` | 边界盒层次结构,用于加速绘制 |
| `fDrawableList` | `std::unique_ptr<SkDrawableList>` | 嵌套的可绘制对象列表 |
| `fBounds` | `const SkRect` | 绘制内容的边界矩形 |

## 公共 API 函数

### 构造函数

```cpp
SkRecordedDrawable(sk_sp<SkRecord> record,
                   sk_sp<SkBBoxHierarchy> bbh,
                   std::unique_ptr<SkDrawableList> drawableList,
                   const SkRect& bounds)
```
构造一个录制的可绘制对象,接受录制数据、BBH、可绘制列表和边界。

### 序列化方法

```cpp
void flatten(SkWriteBuffer& buffer) const override
```
将 `SkRecordedDrawable` 序列化到缓冲区,用于持久化或传输。实现过程:
1. 写入边界矩形
2. 创建 `SkPictureRecord` 重放命令
3. 转换为 `SkPictureData` 并序列化

### 静态工厂方法

```cpp
static sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer)
```
从序列化缓冲区反序列化创建 `SkRecordedDrawable` 对象。

## 内部实现细节

### onDraw 方法

```cpp
void onDraw(SkCanvas* canvas) override
```
将录制的命令回放到指定的画布上:
1. 准备可绘制对象数组(如果有)
2. 调用 `SkRecordDraw` 执行回放,利用 BBH 优化裁剪区域

### onGetBounds 方法

```cpp
SkRect onGetBounds() override
```
返回存储的边界矩形 `fBounds`,用于快速剪裁判断。

### onApproximateBytesUsed 方法

```cpp
size_t onApproximateBytesUsed() override
```
计算对象占用的内存:
- 对象自身大小
- `SkRecord` 使用的字节数
- BBH 使用的字节数
- 所有嵌套 drawable 的内存总和

### onMakePictureSnapshot 方法

```cpp
sk_sp<SkPicture> onMakePictureSnapshot() override
```
创建不可变的 `SkPicture` 快照:
1. 从 `fDrawableList` 创建图片快照数组
2. 计算子图片的总字节数
3. 返回新的 `SkBigPicture` 对象

### 序列化实现

`flatten` 方法通过创建临时 `SkPictureRecord` 来重放命令:
- 如果查询包含整个图片,跳过 BBH 以提高效率
- 将命令录制到 `SkPictureRecord`
- 转换为 `SkPictureData` 后序列化

反序列化通过 `CreateProc`:
- 读取边界矩形
- 使用 `SkPictureData::CreateFromBuffer` 反序列化
- 通过 `SkPicturePlayback` 和 `SkPictureRecorder` 重建 drawable

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecord` | 存储录制的绘图命令 |
| `SkBBoxHierarchy` | 提供空间索引加速绘制 |
| `SkDrawableList` | 管理嵌套的可绘制对象 |
| `SkRecordDraw` | 执行录制命令的回放 |
| `SkBigPicture` | 创建不可变的图片快照 |
| `SkPictureData` | 序列化支持 |
| `SkPictureRecord` | 重录制命令以支持序列化 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPictureRecorder` | 通过 `finishRecordingAsDrawable()` 创建 |
| 客户端代码 | 作为可复用的绘图内容 |
| 序列化系统 | 通过 flattenable 机制持久化 |

## 设计模式与设计决策

### 1. 适配器模式
将 `SkRecord` 的底层表示适配为 `SkDrawable` 接口,提供统一的绘制抽象。

### 2. 快照模式
通过 `onMakePictureSnapshot()` 创建不可变的图片副本,确保原始录制内容可以被安全共享和缓存。

### 3. 延迟计算
边界和内存使用信息存储而非每次计算,提高查询效率。

### 4. 组合模式
通过 `fDrawableList` 支持嵌套的可绘制对象,形成绘图对象树。

### 5. 序列化策略
序列化时不直接序列化 `SkRecord`,而是通过 `SkPictureRecord` 重放并转换为 `SkPictureData`,这提供了更好的兼容性和压缩。

## 性能考量

### 1. BBH 优化
存储 `SkBBoxHierarchy` 允许在绘制时跳过不在裁剪区域内的命令,显著提升大型场景的绘制性能。

### 2. 智能 BBH 使用
在 `flatten` 中,如果查询包含整个图片,自动跳过 BBH 以避免不必要的开销。

### 3. 共享所有权
使用 `sk_sp<SkRecord>` 智能指针,允许多个 drawable 共享同一录制数据,节省内存。

### 4. 内存追踪
`onApproximateBytesUsed()` 提供准确的内存占用估算,帮助实现有效的缓存策略。

### 5. 嵌套对象处理
递归计算所有嵌套 drawable 的内存使用和快照,确保完整的资源管理。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 录制命令的存储结构 |
| `src/core/SkRecordDraw.h` | 命令回放实现 |
| `src/core/SkRecordCanvas.h` | 录制命令的画布 |
| `include/core/SkDrawable.h` | 基类定义 |
| `include/core/SkBBHFactory.h` | BBH 工厂接口 |
| `src/core/SkBigPicture.h` | 图片快照实现 |
| `src/core/SkPictureData.h` | 序列化数据格式 |
| `src/core/SkPictureRecord.h` | 录制辅助类 |
| `include/core/SkPictureRecorder.h` | 创建 drawable 的录制器 |
