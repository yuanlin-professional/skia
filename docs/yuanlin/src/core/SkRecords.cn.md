# SkRecords

> 源文件: src/core/SkRecords.h, src/core/SkRecords.cpp

## 概述

`SkRecords` 定义了 Skia 录制系统中所有可能的画布操作类型。每个 Canvas API 调用(如 `drawRect`、`save`、`translate` 等)都对应一个具体的记录结构体。这些结构体以紧凑的形式存储绘图命令和参数,用于延迟执行、优化和序列化。该模块是 Skia 录制机制的类型系统核心。

## 架构位置

`SkRecords` 位于 Skia 绘图引擎的核心录制层:
- 被 `SkRecordCanvas` 用于录制 Canvas 调用
- 被 `SkRecord` 容器存储
- 被 `SkRecordDraw` 回放到 Canvas
- 被 `SkRecordOpts` 进行模式匹配优化
- 为整个录制-优化-回放流程提供统一的类型定义

## 主要类与结构体

### 命令类型枚举

```cpp
enum Type {
    NoOp_Type, Restore_Type, Save_Type, SaveLayer_Type, ...
};
```

通过宏 `SK_RECORD_TYPES` 定义所有命令类型,自动生成枚举。

### 标签系统(Tags)

| 标签 | 值 | 含义 |
|-----|-----|------|
| `kDraw_Tag` | 1 | 可能绘制内容 |
| `kHasImage_Tag` | 2 | 包含 SkImage 或 SkBitmap |
| `kHasText_Tag` | 4 | 包含文本 |
| `kHasPaint_Tag` | 8 | 包含 SkPaint(可能可选) |
| `kMultiDraw_Tag` | 16 | 多图元绘制,可能自混合 |
| `kDrawWithPaint_Tag` | 25 | kDraw_Tag | kHasPaint_Tag 的组合 |

### 辅助模板类

#### Optional<T>

**功能:** 管理可选参数的生命周期,不拥有内存但负责析构。

**继承关系:**
- 独立模板类
- 移动语义支持,禁止拷贝

**关键成员:**
- `T* fPtr`: 指向 SkRecord arena 分配的内存
- 析构时调用 `fPtr->~T()`

#### PODArray<T>

**功能:** 指向 POD 类型数组的轻量级指针包装。

**特点:**
- 不拥有内存
- 支持默认拷贝和赋值
- 提供 `operator T*()` 隐式转换

#### PreCachedPath

**继承关系:** `SkPath`

**功能:** 预缓存路径的边界和方向信息,确保线程安全。

**实现:**
```cpp
PreCachedPath::PreCachedPath(const SkPath& path) : SkPath(path) {
    this->updateBoundsCache();
    (void)this->getGenerationID();
}
```

#### TypedMatrix

**继承关系:** `SkMatrix`

**功能:** 预缓存矩阵类型,避免回放时的重复计算。

**实现:**
```cpp
TypedMatrix::TypedMatrix(const SkMatrix& matrix) : SkMatrix(matrix) {
    (void)this->getType();
}
```

#### ClipOpAndAA

**功能:** 紧凑地存储裁剪操作和抗锯齿标志。

**内存布局:**
```cpp
unsigned fOp : 31;  // SkClipOp
unsigned fAA :  1;  // bool
```
仅占用 4 字节。

### 主要命令结构体

#### 状态管理命令

**NoOp:**
- 无操作占位符
- 标签: 0

**Save:**
- 保存当前画布状态
- 标签: 0

**Restore:**
- 恢复画布状态
- 成员: `TypedMatrix matrix` (恢复后的矩阵)

**SaveLayer:**
- 创建离屏层
- 成员:
  - `Optional<SkRect> bounds`
  - `Optional<SkPaint> paint`
  - `sk_sp<const SkImageFilter> backdrop`
  - `SkCanvas::SaveLayerFlags saveLayerFlags`
  - `SkScalar backdropScale`
  - `SkTileMode backdropTileMode`
  - `skia_private::AutoTArray<sk_sp<SkImageFilter>> filters`
- 标签: `kHasPaint_Tag`

**SaveBehind:**
- 保存子集区域(用于特殊效果)
- 成员: `Optional<SkRect> subset`

#### 变换命令

**SetMatrix:**
- 设置绝对变换矩阵
- 成员: `TypedMatrix matrix`

**SetM44:**
- 设置 4x4 变换矩阵
- 成员: `SkM44 matrix`

**Concat / Concat44:**
- 连接变换矩阵
- 成员: `TypedMatrix matrix` / `SkM44 matrix`

**Translate:**
- 平移变换
- 成员: `SkScalar dx, dy`

**Scale:**
- 缩放变换
- 成员: `SkScalar sx, sy`

#### 裁剪命令

**ClipRect / ClipRRect / ClipPath:**
- 矩形/圆角矩形/路径裁剪
- 成员: 几何形状 + `ClipOpAndAA opAA`

**ClipRegion:**
- 区域裁剪
- 成员: `SkRegion region` + `SkClipOp op`

**ClipShader:**
- 着色器裁剪(alpha 蒙版)
- 成员: `sk_sp<SkShader> shader` + `SkClipOp op`

**ResetClip:**
- 重置裁剪到设备边界

#### 绘制命令

**DrawPaint:**
- 填充整个画布
- 成员: `SkPaint paint`
- 标签: `kDrawWithPaint_Tag`

**DrawRect / DrawOval / DrawRRect:**
- 基本形状绘制
- 成员: `SkPaint paint` + 几何参数

**DrawPath:**
- 路径绘制
- 成员: `SkPaint paint` + `PreCachedPath path`

**DrawImage:**
- 图像绘制
- 成员:
  - `Optional<SkPaint> paint`
  - `sk_sp<const SkImage> image`
  - `SkScalar left, top`
  - `SkSamplingOptions sampling`
- 标签: `kDraw_Tag | kHasImage_Tag | kHasPaint_Tag`

**DrawImageRect:**
- 图像矩形绘制
- 额外成员: `SkRect src, dst` + `SrcRectConstraint constraint`

**DrawImageLattice:**
- 九宫格图像绘制
- 复杂的网格分割参数

**DrawTextBlob:**
- 文本块绘制
- 成员: `SkPaint paint` + `sk_sp<const SkTextBlob> blob` + `SkScalar x, y`
- 标签: `kDraw_Tag | kHasText_Tag | kHasPaint_Tag`

**DrawSlug:**
- GPU 文本绘制
- 成员: `SkPaint paint` + `sk_sp<const sktext::gpu::Slug> slug`

**DrawVertices:**
- 顶点绘制
- 成员: `SkPaint paint` + `sk_sp<SkVertices> vertices` + `SkBlendMode bmode`
- 标签: `kDraw_Tag | kHasPaint_Tag | kMultiDraw_Tag`

**DrawMesh:**
- 网格绘制
- 成员: `SkPaint paint` + `SkMesh mesh` + `sk_sp<SkBlender> blender`

**DrawAtlas:**
- 图集批量绘制
- 成员包括变换数组、纹理坐标数组等
- 标签: `kDraw_Tag | kHasImage_Tag | kHasPaint_Tag | kMultiDraw_Tag`

**DrawShadowRec:**
- 阴影绘制
- 成员: `PreCachedPath path` + `SkDrawShadowRec rec`

**DrawAnnotation:**
- 注解(不绘制)
- 成员: `SkRect rect` + `SkString key` + `sk_sp<SkData> value`
- 标签: 0 (技术上是绘制但不产生像素)

**DrawEdgeAAQuad / DrawEdgeAAImageSet:**
- 边缘抗锯齿的四边形/图像集绘制
- Chrome 实验性 API

## 公共 API 函数

### RECORD 宏

```cpp
#define RECORD(T, tags, ...) \
    struct T { \
        static const Type kType = T##_Type; \
        static const int kTags = tags; \
        __VA_ARGS__; \
    };
```

**功能:** 简化命令结构体定义,自动添加类型和标签。

### SK_RECORD_TYPES 宏

定义所有命令类型的列表,用于:
- 生成 `enum Type`
- `SkRecord::visit/mutate` 的 switch 语句
- 其他需要枚举所有类型的代码

### PreCachedPath / TypedMatrix 构造函数

预计算线程安全所需的缓存信息。

## 内部实现细节

### 内存布局优化

- 将 `SkPaint` 放在结构体首部以提高缓存命中率
- 使用位域压缩 `ClipOpAndAA` 到 4 字节
- `Optional<T>` 仅存储指针,避免不必要的对象拷贝

### 宏展开示例

```cpp
SK_RECORD_TYPES(M)
// 展开为:
M(NoOp) M(Restore) M(Save) ... M(DrawEdgeAAImageSet)
```

### 类型安全

- 每个命令都有唯一的 `kType` 常量
- `SkRecord` 通过类型 ID 实现多态 visit/mutate

### POD vs 非 POD

- PODArray 用于简单类型(如 `SkPoint`, `int`)
- Optional 用于需要析构的类型(如 `SkPaint`, `SkRect`)

### 图像与文本标签

通过 `kHasImage_Tag` 和 `kHasText_Tag`,系统可以:
- 快速统计资源使用
- 实现特定优化(如文本子像素定位)
- 分析绘制复杂度

### MultiDraw 标签

标记如 `DrawAtlas`、`DrawVertices` 等可能渲染多个重叠图元的命令,这些命令:
- 不能简单合并 SaveLayer 透明度(会改变自混合结果)
- 需要特殊的优化策略

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPaint` | 绘制属性 |
| `SkPath` | 路径几何 |
| `SkImage` | 图像资源 |
| `SkTextBlob` | 文本数据 |
| `SkVertices` / `SkMesh` | 顶点数据 |
| `SkImageFilter` | 图像滤镜 |
| `SkMatrix` / `SkM44` | 变换矩阵 |
| `SkRegion` | 裁剪区域 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkRecord` | 存储这些命令 |
| `SkRecordCanvas` | 创建这些命令 |
| `SkRecordDraw` | 回放这些命令 |
| `SkRecordOpts` | 优化这些命令 |
| `SkRecordPattern` | 模式匹配这些命令 |

## 设计模式与设计决策

### 1. 值语义
所有命令结构体都是 POD 或接近 POD,支持浅拷贝和内存布局优化。

### 2. 标签分派
使用编译期常量标签实现快速类型查询,无需运行时类型信息。

### 3. 宏元编程
通过 `SK_RECORD_TYPES` 宏维护单一真实来源,减少代码重复和错误。

### 4. 缓存友好设计
- 将最常访问的字段(如 `SkPaint`)放在结构体开头
- 使用紧凑的数据表示减少缓存行占用

### 5. 延迟绑定
使用智能指针(`sk_sp`)和 Optional 语义,避免不必要的资源拷贝。

### 6. 平台兼容性
某些命令(如 `DrawEdgeAAImageSet`)标记为 Chrome 专用,保持 API 灵活性。

### 7. 多态访问
虽然结构体本身不是多态的,但通过 `SkRecord::visit` 和类型 ID 实现了一种"类型擦除"的多态。

## 性能考量

### 1. 紧凑内存表示
使用位域和 Optional 减少内存占用,提高缓存效率。

### 2. 预缓存关键信息
`PreCachedPath` 和 `TypedMatrix` 避免回放时的重复计算。

### 3. 避免虚函数
所有命令都是普通结构体,无虚表开销。

### 4. 批量数据存储
使用 `PODArray` 引用 arena 分配的数组,避免多次分配。

### 5. 智能指针开销
对于大对象(如 `SkImage`)使用 `sk_sp` 引用计数,避免深拷贝。

### 6. 标签查询优化
标签是编译期常量,查询可被优化为位运算。

### 7. 命令顺序优化
`SK_RECORD_TYPES` 中命令的顺序经过考虑:
- NoOp 在首位(最常见的优化结果)
- 语义相关的命令分组(提高 CPU 分支预测)

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 存储命令序列的容器 |
| `src/core/SkRecordCanvas.h` | 创建这些命令 |
| `src/core/SkRecordDraw.h` | 回放这些命令 |
| `src/core/SkRecordOpts.h` | 优化这些命令 |
| `src/core/SkRecordPattern.h` | 模式匹配框架 |
| `include/core/SkCanvas.h` | 原始 Canvas API |
| `include/core/SkPaint.h` | 绘制属性 |
| `include/core/SkPath.h` | 路径几何 |
| `include/core/SkImage.h` | 图像资源 |
| `include/core/SkTextBlob.h` | 文本数据 |
| `include/core/SkImageFilter.h` | 图像滤镜 |
| `src/core/SkDrawShadowInfo.h` | 阴影参数 |
