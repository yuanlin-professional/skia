# SkBitmapProcShader

> 源文件
> - src/shaders/SkBitmapProcShader.h
> - src/shaders/SkBitmapProcShader.cpp

## 概述

`SkBitmapProcLegacyShader` 是 Skia 中用于支持旧版位图处理的着色器实现。它提供了一个传统的上下文驱动的位图采样路径,主要用于不支持现代光栅管线的场景。该着色器通过 `SkBitmapProcState` 执行矩阵变换和像素采样,使用分块处理策略来高效地渲染位图。

这是一个遗留组件,主要为了向后兼容性而保留。现代代码路径通常使用 `SkImageShader` 配合光栅管线来实现相同功能,但在某些特定平台或配置下,这个旧版实现仍然可能被调用。

## 架构位置

`SkBitmapProcLegacyShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **友元类**: `SkImageShader` (唯一可以访问其功能的类)
- **角色**: 遗留位图处理路径的入口点

该类在着色器系统中属于特殊类别:
- 不直接实例化(没有公共构造函数)
- 仅通过 `MakeContext()` 静态方法被 `SkImageShader` 使用
- 在上下文驱动的渲染路径中作为后备实现

## 主要类与结构体

### SkBitmapProcLegacyShader

遗留位图处理着色器的外壳类。

**关键特性**:
- 没有数据成员
- 没有实例方法
- 仅提供一个静态工厂方法

**核心方法**:
```cpp
static Context* MakeContext(
    const SkShaderBase& shader,
    SkTileMode tmx, SkTileMode tmy,
    const SkSamplingOptions& sampling,
    const SkImage_Base* image,
    const ContextRec& rec,
    SkArenaAlloc* alloc
);
```

### BitmapProcShaderContext

实际执行位图采样的上下文类。

**成员变量**:
```cpp
SkBitmapProcState* fState;  // 位图处理状态机
uint32_t fFlags;            // 着色器标志(例如不透明性)
```

**关键方法**:
- `BitmapProcShaderContext()`: 构造函数,初始化状态和标志
- `uint32_t getFlags() const`: 返回着色器标志
- `void shadeSpan(int x, int y, SkPMColor dstC[], int count)`: 着色一行像素

### SkBitmapProcState

位图处理状态机(在 `src/core/SkBitmapProcState.h` 中定义),负责:
- 矩阵变换
- 瓦片模式处理
- 像素采样
- 过滤和插值

## 公共 API 函数

### SkBitmapProcLegacyShader::MakeContext()

创建位图处理上下文用于渲染。

**参数**:
- `shader`: 着色器基类引用
- `tmx`, `tmy`: X 和 Y 方向的瓦片模式
- `sampling`: 采样选项(过滤器、mipmap 等)
- `image`: 要渲染的图像
- `rec`: 上下文记录,包含矩阵、画笔 alpha 等
- `alloc`: 竞技场分配器,用于分配上下文对象

**返回值**:
- 成功时返回 `BitmapProcShaderContext` 指针
- 失败时返回 `nullptr`

**失败条件**:
1. 矩阵不可逆
2. `SkBitmapProcState::setup()` 失败

**实现流程**:
```cpp
auto totalInverse = rec.fMatrixRec.totalInverse();
if (!totalInverse) {
    return nullptr;  // 矩阵不可逆
}

SkBitmapProcState* state = alloc->make<SkBitmapProcState>(image, tmx, tmy);
if (!state->setup(*totalInverse, rec.fPaintAlpha, sampling)) {
    return nullptr;  // 设置失败
}
return alloc->make<BitmapProcShaderContext>(shader, rec, state);
```

## 内部实现细节

### BitmapProcShaderContext 构造

构造函数初始化标志位,特别是检查不透明性:

```cpp
BitmapProcShaderContext(const SkShaderBase& shader, const SkShaderBase::ContextRec& rec,
                        SkBitmapProcState* state)
    : INHERITED(shader, rec)
    , fState(state)
    , fFlags(0)
{
    if (fState->fPixmap.isOpaque() && (255 == this->getPaintAlpha())) {
        fFlags |= SkShaderBase::kOpaqueAlpha_Flag;
    }
}
```

**不透明性检测**:
- 图像必须是不透明的 (`fPixmap.isOpaque()`)
- 画笔 alpha 必须是完全不透明的 (255)
- 两者都满足时设置 `kOpaqueAlpha_Flag`

这个标志允许后续的渲染优化,例如跳过混合操作。

### shadeSpan() 实现

`shadeSpan()` 是核心的着色方法,负责填充一行像素。它使用两种策略:

#### 快速路径 (Shader Proc)

```cpp
if (state.getShaderProc32()) {
    state.getShaderProc32()(&state, x, y, dstC, count);
    return;
}
```

如果 `SkBitmapProcState` 提供了优化的着色器过程,直接使用它一次性处理所有像素。

#### 分块处理路径

当没有快速着色器过程时,使用分块策略:

```cpp
const int BUF_MAX = 128;
uint32_t buffer[BUF_MAX];
SkBitmapProcState::MatrixProc mproc = state.getMatrixProc();
SkBitmapProcState::SampleProc32 sproc = state.getSampleProc32();
const int max = state.maxCountForBufferSize(sizeof(buffer[0]) * BUF_MAX);

for (;;) {
    int n = std::min(count, max);
    mproc(state, buffer, n, x, y);  // 矩阵变换
    sproc(state, buffer, n, dstC);   // 像素采样

    if ((count -= n) == 0) break;
    x += n;
    dstC += n;
}
```

**分块处理优势**:
1. **固定缓冲区**: 使用栈上的 128 元素缓冲区,避免动态分配
2. **缓存友好**: 小缓冲区保持在 CPU 缓存中
3. **分离关注点**: 矩阵变换和采样分离,便于优化
4. **灵活性**: `maxCountForBufferSize()` 根据采样需求调整块大小

### 两阶段处理

分块路径使用两个函数指针:

1. **MatrixProc** (`mproc`):
   - 将屏幕坐标转换为纹理坐标
   - 应用瓦片模式
   - 输出到中间缓冲区

2. **SampleProc32** (`sproc`):
   - 从纹理坐标采样像素
   - 应用过滤(最近邻、双线性等)
   - 输出最终颜色到目标缓冲区

这种分离允许为不同的矩阵类型和采样模式选择专门的实现。

### 矩阵逆变换

在 `MakeContext()` 中,首先计算总矩阵的逆:

```cpp
auto totalInverse = rec.fMatrixRec.totalInverse();
if (!totalInverse) {
    return nullptr;
}
```

这是必需的,因为着色需要从屏幕空间映射回纹理空间。如果矩阵不可逆(例如包含投影到线或点的变换),着色无法进行。

### 友元访问限制

```cpp
class SkBitmapProcLegacyShader : public SkShaderBase {
private:
    friend class SkImageShader;

    static Context* MakeContext(...);
    // ...
};
```

`MakeContext()` 是私有的,只有 `SkImageShader` 作为友元可以调用。这强制所有位图着色通过 `SkImageShader`,保持架构清晰。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类和上下文框架
- **SkBitmapProcState**: 核心位图处理状态机
- **SkImage_Base**: 图像数据访问
- **SkSamplingOptions**: 采样配置
- **SkTileMode**: 瓦片模式枚举
- **SkArenaAlloc**: 内存分配
- **SkPixmap**: 像素数据访问

### 被依赖关系

- **SkImageShader**: 唯一调用者,在不支持管线路径时使用

### 与现代路径的关系

```
                ┌─────────────────┐
                │  SkImageShader  │
                └────────┬────────┘
                         │
            ┌────────────┼────────────┐
            │                         │
      [Modern Path]             [Legacy Path]
    RasterPipeline          SkBitmapProcLegacyShader
            │                         │
    appendStages()              MakeContext()
            │                         │
        SkRP Ops              SkBitmapProcState
```

## 设计模式与设计决策

### 策略模式

`SkBitmapProcState` 使用策略模式选择矩阵和采样过程:
- 根据矩阵类型选择 `MatrixProc`
- 根据采样选项选择 `SampleProc32`
- 如果可能,选择组合的 `ShaderProc32`

### 上下文对象模式

`BitmapProcShaderContext` 封装着色状态:
- 包含所有着色所需信息
- 支持增量渲染 (`shadeSpan()` 可多次调用)
- 通过竞技场分配器高效管理生命周期

### 友元模式限制访问

使用友元关系而不是公共接口:
- 防止直接使用遗留路径
- 强制通过 `SkImageShader` 的统一入口
- 保留未来完全移除的灵活性

### 遗留支持设计

这是一个"遗留"类的特征:
- 最小化公共接口
- 封装在现代实现内部
- 仅在必要时激活
- 为未来废弃做好准备

### 分块处理策略

固定大小缓冲区的设计权衡:
- **优点**: 无动态分配、缓存友好、可预测性能
- **缺点**: 长行需要多次循环
- **结论**: 对于典型使用场景(短到中等长度的扫描线),这是最优的

## 性能考量

### 快速路径优化

优先使用 `getShaderProc32()`:
- 单次函数调用处理整行
- 可能使用专门优化的实现(SIMD 等)
- 避免中间缓冲区和循环开销

### 固定缓冲区大小

128 元素缓冲区的选择:
- 512 字节(128 × 4),适合 L1 缓存
- 足够大以分摊函数调用开销
- 足够小以避免缓存污染

### 函数指针调用

使用函数指针而不是虚函数:
- 避免虚函数表查找
- 在循环外选择一次,在循环内快速调用
- 编译器可能内联某些实现

### 不透明性优化

在构造时检测不透明性:
- 设置标志后,调用者可以跳过混合
- 可能使用更快的 `memcpy` 路径
- 减少内存带宽需求

### 竞技场分配

所有对象在竞技场中分配:
- 单次分配多个对象
- 统一释放,无碎片
- 缓存局部性好

### 向量化潜力

分块处理为 SIMD 优化创造机会:
- 固定大小便于向量化
- 矩阵和采样过程可以使用 SIMD
- 128 元素是常见 SIMD 宽度的良好倍数

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类定义
- `src/core/SkBitmapProcState.h` - 位图处理状态机
- `src/core/SkBitmapProcState.cpp` - 状态机实现

### 图像处理
- `src/shaders/SkImageShader.h` - 现代图像着色器(调用者)
- `src/shaders/SkImageShader.cpp` - 图像着色器实现
- `src/core/SkImage_Base.h` - 图像基类

### 采样与过滤
- `include/core/SkSamplingOptions.h` - 采样选项定义
- `include/core/SkTileMode.h` - 瓦片模式枚举
- `include/core/SkPixmap.h` - 像素映射

### 内存与性能
- `src/base/SkArenaAlloc.h` - 竞技场分配器
- `include/core/SkMatrix.h` - 矩阵变换

### 现代替代方案
- `src/core/SkRasterPipeline.h` - 现代光栅管线
- `src/core/SkRasterPipelineOpList.h` - 管线操作

### 颜色处理
- `include/core/SkColor.h` - 颜色定义(`SkPMColor` 等)
- `src/core/SkColorSpaceXformSteps.h` - 色彩空间转换

### 调试与断言
- `include/private/base/SkAssert.h` - 断言宏
