# SkEffectPriv

> 源文件
> - src/core/SkEffectPriv.h

## 概述

`SkEffectPriv.h` 是 Skia 内部使用的效果处理私有头文件,定义了 `SkStageRec` 结构体,该结构体封装了向光栅管线(raster pipeline)添加阶段时所需的所有上下文信息。这个文件为各种图形效果(如着色器、颜色滤镜、图像滤镜等)提供了统一的管线集成接口,是 Skia 现代光栅化架构的关键组成部分。

`SkStageRec` 作为参数传递给效果对象的 `appendStages` 方法,使效果能够将自己的处理逻辑添加到光栅管线中。它包含了管线指针、内存分配器、目标颜色空间、画笔颜色等关键信息,确保效果能够正确地集成到渲染流程中。

## 架构位置

`SkEffectPriv` 在 Skia 光栅化管线架构中起桥梁作用:

```
效果对象(Shader, ColorFilter, ImageFilter等)
    ↓
SkStageRec (效果→管线集成接口)
    ↓
SkRasterPipeline (光栅管线)
    ↓
像素处理阶段
    ↓
SkBlitter (像素写入)
```

**关键交互**:
- **效果对象**: 使用 `SkStageRec` 添加管线阶段
- **SkRasterPipeline**: 接收并执行添加的阶段
- **SkArenaAlloc**: 为管线阶段数据分配内存

## 主要类与结构体

### SkStageRec

**类型**: 结构体(struct)

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPipeline` | `SkRasterPipeline*` | 指向光栅管线的指针,效果通过它添加处理阶段 |
| `fAlloc` | `SkArenaAlloc*` | 内存分配器指针,用于分配管线阶段所需的数据结构 |
| `fDstColorType` | `SkColorType` | 目标颜色类型(如 RGBA_8888, RGBA_F16 等) |
| `fDstCS` | `SkColorSpace*` | 目标颜色空间指针,可能为 nullptr(表示无颜色管理) |
| `fPaintColor` | `SkColor4f` | 画笔颜色,使用浮点 RGBA 表示 |
| `fSurfaceProps` | `const SkSurfaceProps&` | 表面属性的常量引用,包含像素几何信息 |
| `fDstBounds` | `SkRect` | 设备空间中绘制几何的边界框,用于优化启发式算法 |

## 公共 API 函数

`SkEffectPriv.h` 仅定义数据结构,不包含函数定义。`SkStageRec` 作为参数被以下类型的效果对象使用:

### 效果对象接口(约定)

```cpp
// 着色器
bool SkShader::appendStages(const SkStageRec& rec, const SkShaders::MatrixRec&) const;

// 颜色滤镜
bool SkColorFilter::appendStages(const SkStageRec& rec, bool shaderIsOpaque) const;

// 图像滤镜
// 使用 SkStageRec 构建图像处理管线

// 混合器
bool SkBlender::appendStages(const SkStageRec& rec) const;
```

**返回值**:
- `true`: 成功添加管线阶段
- `false`: 无法使用管线实现,需要回退到其他渲染路径

## 内部实现细节

### SkStageRec 的使用模式

**典型用法**:
```cpp
bool MyEffect::appendStages(const SkStageRec& rec, ...) const {
    // 1. 从 arena 分配器分配数据
    auto* data = rec.fAlloc->make<MyStageData>();
    data->setup(...);

    // 2. 添加管线阶段
    rec.fPipeline->append(SkRasterPipelineOp::my_effect, data);

    // 3. 可能添加多个阶段
    rec.fPipeline->append(SkRasterPipelineOp::another_stage);

    return true;
}
```

### fDstBounds 的用途

`fDstBounds` 提供绘制区域的边界信息,用于优化决策:

**使用场景**:
1. **避免不必要的计算**: 如果边界框为空或很小,可以选择简化的实现
2. **纹理采样优化**: 根据边界大小选择不同的采样策略
3. **LOD 选择**: 为图像滤镜选择合适的细节级别

**空值处理**:
```cpp
if (rec.fDstBounds.isEmpty()) {
    // 边界未知或计算代价高,使用保守策略
}
```

### fDstCS 的空值语义

`fDstCS` 可能为 `nullptr`:
- **含义**: 不进行颜色空间转换,工作在设备颜色空间
- **使用**: 效果需要检查并决定是否需要颜色管理

```cpp
bool MyEffect::appendStages(const SkStageRec& rec, ...) const {
    if (rec.fDstCS) {
        // 添加颜色空间转换阶段
        rec.fPipeline->append_from_srgb(...);
    }
    // 添加效果的核心处理阶段
    ...
}
```

### fAlloc 的内存管理

`SkArenaAlloc` 提供快速的栈式内存分配:

**特性**:
- **快速分配**: 接近栈分配的速度
- **批量释放**: 管线执行完毕后统一释放,无需逐个释放
- **对齐保证**: 自动处理内存对齐

**典型使用**:
```cpp
struct MyStageCtx {
    SkMatrix matrix;
    float parameters[4];
};

auto* ctx = rec.fAlloc->make<MyStageCtx>();
ctx->matrix = ...;
ctx->parameters[0] = ...;

rec.fPipeline->append(my_stage_op, ctx);
```

### fPaintColor 的用途

`fPaintColor` 传递画笔的颜色信息:

**使用场景**:
1. **着色器调制**: 着色器输出与画笔颜色混合
2. **alpha 预乘**: 应用画笔的 alpha 值
3. **颜色源**: 某些效果直接使用画笔颜色

```cpp
// 着色器示例
rec.fPipeline->append(shader_stage, ...);
rec.fPipeline->append(SkRasterPipelineOp::scale_1_float,
                      &rec.fPaintColor.fA);  // 应用画笔 alpha
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkColor` | 定义 `SkColor4f` 颜色类型 |
| `SkColorType` | 定义目标颜色类型枚举 |
| `SkRect` | 定义边界框 |
| `SkArenaAlloc` | 前向声明,内存分配器 |
| `SkColorSpace` | 前向声明,颜色空间 |
| `SkRasterPipeline` | 前向声明,光栅管线 |
| `SkSurfaceProps` | 前向声明,表面属性 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkShader` | 使用 `SkStageRec` 添加着色器阶段 |
| `SkColorFilter` | 使用 `SkStageRec` 添加颜色滤镜阶段 |
| `SkImageFilter` | 使用 `SkStageRec` 构建滤镜管线 |
| `SkBlender` | 使用 `SkStageRec` 添加混合阶段 |
| `SkMaskFilter` | 使用 `SkStageRec` 添加遮罩处理阶段 |
| `SkRasterPipelineBlitter` | 创建并传递 `SkStageRec` 给效果对象 |

## 设计模式与设计决策

### 参数对象模式

`SkStageRec` 实现了参数对象(Parameter Object)模式:

**优势**:
1. **简化接口**: 将多个相关参数打包为一个对象
2. **易于扩展**: 添加新字段不需要修改所有调用者
3. **语义清晰**: 字段名称明确表达含义

**对比**:
```cpp
// 不使用参数对象(糟糕)
bool appendStages(SkRasterPipeline* pipeline, SkArenaAlloc* alloc,
                  SkColorType dstCT, SkColorSpace* dstCS,
                  SkColor4f paintColor, const SkSurfaceProps& props,
                  SkRect bounds);

// 使用参数对象(清晰)
bool appendStages(const SkStageRec& rec);
```

### 不变性设计

大部分字段为常量引用或指针:
- `fSurfaceProps`: const 引用,不可修改
- `fDstCS`: 指针可为 null,但不修改对象
- `fPipeline` 和 `fAlloc`: 指针,但调用者不应修改指针本身

**原因**:
- 防止意外修改共享状态
- 明确所有权语义
- 便于推理和调试

### 设计决策

1. **结构体而非类**: 使用 `struct` 而非 `class`
   - **原因**: 纯数据容器,无需封装
   - **便利**: 公共成员,无需 getter/setter

2. **指针而非智能指针**: 使用原始指针
   - **原因**: 不涉及所有权转移
   - **生命周期**: 由调用者管理,明确且高效

3. **fDstBounds 可选**: 边界框可能为空
   - **原因**: 计算边界可能代价高昂
   - **权衡**: 效果需要处理未知边界的情况

4. **fDstCS 可为 null**: 颜色空间指针可选
   - **原因**: 不是所有渲染都需要颜色管理
   - **性能**: 避免不必要的颜色空间转换开销

5. **SkSurfaceProps 引用**: 使用引用而非指针
   - **原因**: 表面属性总是有效的
   - **语义**: 明确表示非空约束

## 性能考量

### 内存分配优化

使用 `SkArenaAlloc`:
- **快速分配**: O(1) 时间复杂度
- **无碎片**: 连续内存分配
- **批量释放**: 管线结束后一次性释放

### 避免虚函数调用

`SkStageRec` 为简单结构体:
- 无虚函数表开销
- 成员访问为直接内存访问
- 编译器易于内联和优化

### 引用 vs 拷贝

`fSurfaceProps` 使用引用:
- 避免 `SkSurfaceProps` 对象的拷贝
- 减少栈空间使用
- 保持结构体轻量

### 管线构建开销

高效的管线构建:
```cpp
rec.fPipeline->append(op1, data1);
rec.fPipeline->append(op2, data2);
rec.fPipeline->append(op3, data3);
```
- 阶段添加为 O(1) 操作
- 数据结构在 arena 中连续分配
- 无动态内存分配开销

### 条件编译

根据平台和配置选择不同实现:
```cpp
if (rec.fDstColorType == kRGBA_F16_SkColorType) {
    // 高精度路径
} else {
    // 标准路径
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColor.h` | 依赖 | 颜色类型定义 |
| `include/core/SkColorType.h` | 依赖 | 颜色类型枚举 |
| `include/core/SkRect.h` | 依赖 | 矩形边界框 |
| `src/core/SkArenaAlloc.h` | 依赖 | 内存分配器 |
| `src/core/SkRasterPipeline.h` | 依赖 | 光栅管线 |
| `include/core/SkColorSpace.h` | 依赖 | 颜色空间 |
| `include/core/SkSurfaceProps.h` | 依赖 | 表面属性 |
| `include/core/SkShader.h` | 使用者 | 着色器基类 |
| `include/effects/SkColorFilter.h` | 使用者 | 颜色滤镜基类 |
| `src/core/SkRasterPipelineBlitter.cpp` | 使用者 | 创建并使用 `SkStageRec` |
