# VertexFiller

> 源文件
> - src/text/gpu/VertexFiller.h
> - src/text/gpu/VertexFiller.cpp

## 概述

`VertexFiller` 是 Skia GPU 文本渲染系统中负责管理字形顶点填充数据的核心类。它存储字形的创建矩阵、边界和左上角位置信息，并提供智能的矩阵差异计算功能，使得在不同绘制位置下可以高效重用相同的字形纹理数据。该类支持两种填充模式：直接绘制（整数平移）和变换绘制（任意变换）。

## 架构位置

该组件位于 GPU 文本渲染管道的顶点数据管理层（`src/text/gpu/`）：

```
TextBlob
   ↓
SubRunContainer
   ↓
VertexFiller (顶点数据管理)
   ↓
GPU 顶点缓冲区
```

## 主要类与结构体

### VertexFiller 类

管理字形顶点填充数据的容器类。

**成员变量：**
- `fMaskFormat`: `skgpu::MaskFormat` - 掩码格式（A8、A565 等）
- `fCanDrawDirect`: `bool` - 是否支持直接绘制（整数平移优化）
- `fCreationMatrix`: `SkMatrix` - 字形创建时的变换矩阵
- `fCreationBounds`: `SkRect` - 创建时的边界矩形
- `fLeftTop`: `SkSpan<const SkPoint>` - 所有字形的左上角坐标数组

### FillerType 枚举

```cpp
enum FillerType {
    kIsDirect,        // 直接绘制（整数平移）
    kIsTransformed    // 变换绘制（任意变换）
};
```

## 公共 API 函数

### 构造与创建
```cpp
VertexFiller(skgpu::MaskFormat maskFormat,
             const SkMatrix& creationMatrix,
             SkRect creationBounds,
             SkSpan<const SkPoint> leftTop,
             bool canDrawDirect)
```
构造函数，初始化所有成员。

```cpp
static VertexFiller Make(skgpu::MaskFormat maskType,
                         const SkMatrix& creationMatrix,
                         SkRect creationBounds,
                         SkSpan<const SkPoint> positions,
                         SubRunAllocator* alloc,
                         FillerType fillerType)
```
工厂方法，使用分配器创建 `VertexFiller`。

### 序列化
```cpp
void flatten(SkWriteBuffer& buffer) const
static std::optional<VertexFiller> MakeFromBuffer(SkReadBuffer& buffer,
                                                   SubRunAllocator* alloc)
```
支持序列化和反序列化，用于缓存持久化。

### 查询接口
```cpp
skgpu::MaskFormat maskFormat() const   // 获取掩码格式
bool isLCD() const                      // 是否为 LCD 渲染（A565）
int count() const                       // 字形数量
SkSpan<const SkPoint> topLefts() const // 左上角坐标数组
bool canDrawDirect() const              // 是否支持直接绘制
```

### 矩阵计算
```cpp
std::tuple<bool, SkVector> canUseDirect(const SkMatrix& positionMatrix) const
```
检查给定位置矩阵是否与创建矩阵兼容直接绘制，返回是否兼容及平移向量。

```cpp
SkMatrix viewDifference(const SkMatrix& positionMatrix) const
```
计算从创建矩阵到位置矩阵的视图差异矩阵：
```
viewDifference = positionMatrix * creationMatrix^-1
```

### 边界和变换计算
```cpp
std::tuple<bool, SkRect> deviceRectAndCheckTransform(const SkMatrix& positionMatrix) const
```
返回设备空间的边界矩形，并检查是否为整数平移。

```cpp
std::tuple<SkRect, SkMatrix> boundsAndDeviceMatrix(const SkMatrix& localToDevice,
                                                    SkPoint drawOrigin) const
```
计算考虑绘制原点后的边界和设备矩阵。

## 内部实现细节

### 矩阵兼容性检查（CanUseDirect）

直接绘制的条件：
1. **2x2 子矩阵相同**：缩放和倾斜分量必须完全匹配
2. **无透视变换**：两个矩阵都不能有透视分量
3. **整数平移**：平移差异必须是整数像素

**实现逻辑：**
```cpp
SkVector translation = positionMatrix.mapOrigin() - creationMatrix.mapOrigin();
return {
    creationMatrix.getScaleX() == positionMatrix.getScaleX() &&
    creationMatrix.getScaleY() == positionMatrix.getScaleY() &&
    creationMatrix.getSkewX()  == positionMatrix.getSkewX()  &&
    creationMatrix.getSkewY()  == positionMatrix.getSkewY()  &&
    !positionMatrix.hasPerspective() && !creationMatrix.hasPerspective() &&
    SkScalarIsInt(translation.x()) && SkScalarIsInt(translation.y()),
    translation
};
```

**为什么需要整数平移？**
整数平移保证纹理采样不会改变纹素的访问模式，可以直接重用已光栅化的字形掩码。

### 设备矩形计算（deviceRectAndCheckTransform）

**快速路径（直接绘制）：**
如果支持直接绘制且矩阵兼容，直接偏移创建边界：
```cpp
if (directDrawCompatible) {
    return {true, fCreationBounds.makeOffset(offset)};
}
```

**慢速路径（变换绘制）：**
计算视图差异矩阵并变换边界：
```cpp
SkMatrix viewDifference = SkMatrix::Concat(positionMatrix, inverse);
return {false, viewDifference.mapRect(fCreationBounds)};
```

**奇异矩阵处理：**
如果创建矩阵不可逆，返回空矩形，表示应该丢弃此绘制操作。

### 边界和设备矩阵计算（boundsAndDeviceMatrix）

该方法用于处理包含绘制原点的完整变换：

**兼容矩阵快速路径：**
1. 检查 `localToDevice` 和 `fCreationMatrix` 的 2x2 部分是否相同
2. 计算映射后的原点偏移
3. 如果偏移为整数，返回创建边界和平移矩阵

**通用路径：**
1. 将绘制原点预乘到 `localToDevice`
2. 计算视图差异矩阵
3. 返回创建边界和差异矩阵

### LCD 渲染判断

```cpp
bool isLCD() const { return fMaskFormat == MaskFormat::kA565; }
```

`A565` 格式表示 LCD 次像素渲染，需要特殊处理。

## 依赖关系

**直接依赖：**
- `src/gpu/MaskFormat.h` - 掩码格式定义
- `src/text/gpu/SubRunAllocator.h` - 内存分配器
- `src/core/SkReadBuffer.h` / `SkWriteBuffer.h` - 序列化支持
- `include/core/SkMatrix.h` - 矩阵变换

**使用场景：**
- `SubRunContainer` - 子运行容器
- GPU 文本渲染管道
- 字形图集绘制

## 设计模式与设计决策

### 不可变设计
所有成员变量都是 `const`，一旦创建就不可修改，保证线程安全和缓存一致性。

### 视图差异矩阵策略
通过存储创建矩阵并计算差异矩阵，避免重新光栅化字形，这是 GPU 文本渲染的核心优化。

### 双模式支持
区分直接绘制和变换绘制，为常见的平移场景提供快速路径。

### 序列化支持
支持完整的序列化和反序列化，允许将渲染数据缓存到磁盘，加速冷启动。

### 空间优化
使用 `SkSpan` 而非 `std::vector`，避免额外的内存分配和所有权管理开销。

## 性能考量

### 时间复杂度
- **矩阵兼容性检查**：O(1) - 仅比较 9 个矩阵元素
- **边界计算**：O(1) - 矩阵-矩形乘法
- **直接绘制检测**：O(1) - 快速路径检测

### 空间复杂度
- O(n) - 存储 n 个字形的左上角坐标
- 矩阵和边界为固定大小

### 优化策略
1. **快速路径优先**：整数平移场景直接偏移，避免矩阵运算
2. **矩阵缓存**：存储创建矩阵，避免重复计算逆矩阵
3. **紧凑存储**：仅存储必要的位置信息（左上角），尺寸信息在图集中

### 直接绘制的性能优势
- 避免重新光栅化字形
- 减少 GPU 纹理上传
- 简化顶点变换（仅平移）
- 提高缓存命中率

### 适用场景
- 文本滚动（纯平移）
- UI 元素移动
- 相机平移
- 多次绘制相同文本

## 相关文件

**核心依赖：**
- `src/text/gpu/SubRunAllocator.h` - 内存分配
- `src/gpu/MaskFormat.h` - 掩码格式
- `include/core/SkMatrix.h` - 矩阵运算

**使用此类的模块：**
- `src/text/gpu/SubRunContainer.cpp` - 子运行管理
- `src/text/gpu/TextBlob.cpp` - 文本块实现
- GPU 文本渲染管道的各个组件
