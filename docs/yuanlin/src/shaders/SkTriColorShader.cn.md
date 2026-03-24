# SkTriColorShader

> 源文件
> - src/shaders/SkTriColorShader.h
> - src/shaders/SkTriColorShader.cpp

## 概述

`SkTriColorShader` 是 Skia 中专门用于三角形颜色插值的特殊着色器。它通过重心坐标(barycentric coordinates)在三角形的三个顶点颜色之间进行线性插值,实现平滑的颜色过渡。该着色器主要用于渲染顶点着色的三角形网格,是 GPU 风格顶点着色在 CPU 光栅化器上的实现。

与其他着色器不同,`SkTriColorShader` 支持动态更新功能,可以在不重建管线的情况下为每个三角形更新顶点位置和颜色。这使得它非常适合批量绘制多个三角形,例如在 `drawVertices()` 和 `drawMesh()` 等 API 中使用。

## 架构位置

`SkTriColorShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **角色**: 专用于三角形顶点着色
- **使用场景**: `SkCanvas::drawVertices()`, 网格渲染, 3D 图形

该着色器是几何图形渲染系统的一部分,与顶点数组和三角形拓扑紧密关联。

## 主要类与结构体

### SkTriColorShader

三角形颜色插值着色器。

**核心成员**:
```cpp
Matrix43 fM43;         // 4x3 颜色插值矩阵
SkMatrix fM33;         // 3x3 透视变换矩阵
const bool fIsOpaque;  // 是否不透明
const bool fUsePersp;  // 是否使用透视校正
```

**主要方法**:
- `SkTriColorShader(bool isOpaque, bool usePersp)`: 构造函数
- `bool update()`: 更新三角形数据
- `bool appendStages()`: 添加管线阶段
- `ShaderType type()`: 返回 `ShaderType::kTriColor`

### Matrix43

自定义的 4x3 矩阵,用于颜色插值计算。

**结构**:
```cpp
struct Matrix43 {
    float fMat[12];  // 列主序存储
    void setConcat(const Matrix43 a, const SkMatrix& b);
};
```

**布局**:
```
[0  4  8 ]
[1  5  9 ]
[2  6  10]
[3  7  11]
```

前两列存储颜色差值,第三列存储基础颜色。

## 公共 API 函数

### 构造函数

```cpp
SkTriColorShader(bool isOpaque, bool usePersp)
```

创建三角形颜色着色器。

**参数**:
- `isOpaque`: 所有三角形是否完全不透明
- `usePersp`: 是否需要透视校正插值

**决策**:
- `isOpaque=true`: 允许跳过 alpha 混合优化
- `usePersp=true`: 使用透视校正(更慢但正确),适用于 3D 场景
- `usePersp=false`: 仿射插值(更快),适用于 2D 场景

### update()

```cpp
bool update(const SkMatrix& ctmInv,
            const SkPoint pts[],
            const SkPMColor4f colors[],
            int index0, int index1, int index2)
```

为新三角形更新着色器参数。

**参数**:
- `ctmInv`: 当前变换矩阵的逆
- `pts`: 顶点位置数组
- `colors`: 顶点颜色数组(预乘 alpha)
- `index0, index1, index2`: 三角形的三个顶点索引

**返回值**: 成功返回 `true`,如果三角形退化(面积为零)返回 `false`

**更新内容**:
- 重心坐标变换矩阵
- 颜色插值矩阵
- 合并变换(非透视模式)

**关键特性**: 可以多次调用而无需重建管线,实现高效的批量绘制。

## 内部实现细节

### 重心坐标系统

`update()` 方法构建从屏幕空间到重心空间的变换:

1. **构建三角形变换矩阵**:
   ```cpp
   m.set(0, pts[index1].fX - pts[index0].fX);  // 边1的X分量
   m.set(1, pts[index2].fX - pts[index0].fX);  // 边2的X分量
   m.set(2, pts[index0].fX);                    // 顶点0的X
   m.set(3, pts[index1].fY - pts[index0].fY);  // 边1的Y分量
   m.set(4, pts[index2].fY - pts[index0].fY);  // 边2的Y分量
   m.set(5, pts[index0].fY);                    // 顶点0的Y
   ```
   这个矩阵将重心坐标 `(u, v, 1)` 映射到屏幕空间 `(x, y, 1)`。

2. **求逆得到重心坐标**:
   ```cpp
   if (!m.invert(&im)) {
       return false;  // 三角形退化
   }
   fM33.setConcat(im, ctmInv);
   ```
   逆矩阵将屏幕坐标映射回重心坐标。

3. **构建颜色插值矩阵**:
   ```cpp
   auto c0 = skvx::float4::Load(colors[index0].vec()),
        c1 = skvx::float4::Load(colors[index1].vec()),
        c2 = skvx::float4::Load(colors[index2].vec());

   (c1 - c0).store(&fM43.fMat[0]);  // 第一列:顶点1和0的颜色差
   (c2 - c0).store(&fM43.fMat[4]);  // 第二列:顶点2和0的颜色差
   c0.store(&fM43.fMat[8]);          // 第三列:顶点0的颜色
   ```

### 颜色插值数学

最终颜色计算公式:
```
color = c0 + (c1 - c0) * u + (c2 - c0) * v
```
其中 `(u, v)` 是重心坐标。

使用 SIMD (`skvx::float4`)进行向量化计算,同时处理 RGBA 四个通道。

### 透视校正 vs 仿射插值

**仿射模式** (`fUsePersp=false`):
```cpp
if (!fUsePersp) {
    fM43.setConcat(fM43, fM33);  // 合并矩阵
}
```
将几何变换和颜色插值合并为单个 4x3 矩阵,性能更高。

**透视模式** (`fUsePersp=true`):
分别应用透视变换和颜色插值,确保透视校正的正确性。

### 管线集成

`appendStages()` 添加光栅管线阶段:

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec&) const {
    rec.fPipeline->append(SkRasterPipelineOp::seed_shader);  // 初始化坐标
    if (fUsePersp) {
        rec.fPipeline->append(SkRasterPipelineOp::matrix_perspective, &fM33);
    }
    rec.fPipeline->append(SkRasterPipelineOp::matrix_4x3, &fM43);
    return true;
}
```

**阶段说明**:
1. `seed_shader`: 生成像素坐标 (x, y)
2. `matrix_perspective`: 应用透视变换(如果需要)
3. `matrix_4x3`: 从重心坐标计算颜色

### Matrix43::setConcat()

实现 4x3 矩阵与 3x3 矩阵的乘法:

```cpp
void setConcat(const Matrix43 a, const SkMatrix& b)
```

手动展开矩阵乘法,针对仿射变换优化(无透视分量)。

### 不可序列化设计

```cpp
Factory getFactory() const override { return nullptr; }
const char* getTypeName() const override { return nullptr; }
```

`SkTriColorShader` 不支持序列化:
- 它是短暂的,仅在绘制过程中存在
- 每个三角形都会调用 `update()`,不需要持久化
- 避免序列化复杂的内部状态

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类
- **SkMatrix**: 矩阵变换
- **SkPoint**: 顶点位置
- **SkPMColor4f**: 预乘颜色
- **SkRasterPipeline**: 光栅管线
- **skvx**: SIMD 向量化库

### 被依赖关系

- **SkCanvas::drawVertices()**: 使用此着色器渲染顶点着色的网格
- **SkVertices**: 顶点数据结构
- **网格渲染系统**: 三角形网格批量渲染

### 典型调用流程

```
SkCanvas::drawVertices()
    ↓
创建 SkTriColorShader
    ↓
appendStages() (一次)
    ↓
循环每个三角形:
    update(triangle data)
    执行管线
```

## 设计模式与设计决策

### 可变状态着色器

与大多数不可变着色器不同,`SkTriColorShader` 是可变的:
- `update()` 方法修改内部状态
- 在管线构建后更新参数
- 为批处理优化而设计

这是性能优化的权衡:避免为每个三角形重建管线。

### 双模式设计

支持两种插值模式:
- **仿射模式**: 2D 图形,性能优先
- **透视模式**: 3D 图形,正确性优先

通过 `fUsePersp` 标志在构造时决定,后续无法更改。

### 矩阵分离策略

分离几何变换 (`fM33`) 和颜色插值 (`fM43`):
- 透视模式:分别应用
- 仿射模式:合并为单一变换

这允许在不同场景下选择最优路径。

### SIMD 优化

使用 `skvx::float4` 进行颜色计算:
- 同时处理 RGBA 四个通道
- 利用 CPU SIMD 指令
- 最小化内存访问

### 专用化设计

专门为三角形着色设计:
- 不是通用着色器
- 假设重心坐标系统
- 针对批量三角形优化

这体现了"针对特定用例优化"的设计原则。

## 性能考量

### 批量处理优化

`update()` 方法的关键优势:
- 管线只构建一次
- 每个三角形仅更新参数
- 避免重复的管线设置开销

对于渲染数千个三角形的场景,这是显著的性能提升。

### SIMD 颜色插值

使用向量化操作:
- `skvx::float4` 加载和存储
- 向量减法和加法
- 现代 CPU 上接近 4x 加速

### 矩阵合并

仿射模式下合并矩阵:
- 减少一个管线阶段
- 更少的内存访问
- 更好的缓存利用率

### 透视校正开销

透视模式的额外成本:
- 额外的 `matrix_perspective` 阶段
- 每像素除法操作(透视除法)
- 仅在需要时使用

### 退化三角形检测

快速失败机制:
```cpp
if (!m.invert(&im)) {
    return false;  // 跳过退化三角形
}
```
避免渲染零面积或共线顶点的三角形。

### 内存布局

`Matrix43` 使用列主序:
- 与光栅管线操作匹配
- 顺序内存访问模式
- 向量加载友好

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类
- `src/core/SkRasterPipeline.h` - 光栅管线
- `src/core/SkRasterPipelineOpList.h` - 管线操作定义

### 数学与几何
- `include/core/SkMatrix.h` - 矩阵变换
- `include/core/SkPoint.h` - 点定义
- `src/base/SkVx.h` - SIMD 向量化

### 颜色处理
- `src/core/SkColorData.h` - 颜色数据类型
- `include/core/SkColor.h` - `SkPMColor4f` 定义

### 管线相关
- `src/core/SkEffectPriv.h` - 效果私有工具
- `src/core/SkRasterPipelineOpContexts.h` - 管线上下文

### 使用场景
- `src/core/SkCanvas.cpp` - `drawVertices()` 实现
- `include/core/SkVertices.h` - 顶点数据结构
- `src/core/SkDraw.cpp` - 绘制实现
