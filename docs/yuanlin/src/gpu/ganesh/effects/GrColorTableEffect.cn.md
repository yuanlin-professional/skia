# ColorTableEffect

> 源文件
> - `src/gpu/ganesh/effects/GrColorTableEffect.h`
> - `src/gpu/ganesh/effects/GrColorTableEffect.cpp`

## 概述

`ColorTableEffect` 是 Skia 图形库中实现颜色查找表(LUT - Look-Up Table)效果的片段处理器。该效果通过纹理查找实现颜色通道的重映射,支持对 ARGB 四个通道独立应用查找表变换。这是实现 `SkColorFilter::TableARGB` 的 GPU 加速版本。

颜色查找表是一种常用的图像处理技术,通过预先计算的映射表快速实现复杂的颜色变换,如对比度调整、色调映射、颜色校正等。该效果将查找表存储为 256x4 的纹理,通过采样实现高效的颜色转换。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── 片段处理器层
    ├── GrFragmentProcessor (基类)
    └── 效果实现
        ├── ColorTableEffect (当前类 - 颜色查找表)
        ├── GrTextureEffect (纹理采样)
        └── 其他效果处理器
```

该类是 Ganesh 效果系统中的一个具体实现,用于实现颜色过滤效果。

## 主要类与结构体

### ColorTableEffect

**继承关系**
- 继承自: `GrFragmentProcessor` - Ganesh 片段处理器基类

**关键成员变量**

该类不包含显式成员变量,所有数据通过子处理器管理:
- 子处理器 0 (`kTexEffectFPIndex`): `GrTextureEffect` - 查找表纹理
- 子处理器 1 (`kInputFPIndex`): 输入片段处理器 - 源颜色

**常量定义**

| 常量 | 值 | 说明 |
|------|-----|------|
| `kTexEffectFPIndex` | 0 | 查找表纹理效果的子处理器索引 |
| `kInputFPIndex` | 1 | 输入颜色的子处理器索引 |

## 公共 API 函数

### 工厂方法

```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> inputFP,
    GrRecordingContext* context,
    const GrMippedBitmap& bitmap);
```

创建颜色查找表效果处理器。

**参数说明:**
- `inputFP` - 输入片段处理器,提供待处理的颜色
- `context` - 录制上下文,用于创建纹理
- `bitmap` - 查找表位图,格式为 256x4,每行对应一个颜色通道

**返回:** 成功返回效果处理器智能指针,失败返回 `nullptr`

**前置条件:** 位图必须是预乘 alpha 格式(`kPremul_SkAlphaType`)

### 克隆方法

```cpp
std::unique_ptr<GrFragmentProcessor> clone() const override;
```

创建效果的深拷贝,用于管线缓存和多次使用同一效果。

### 名称查询

```cpp
const char* name() const override;
```

返回效果名称 "ColorTableEffect",用于调试和日志。

## 内部实现细节

### 查找表纹理格式

查找表存储为 256x4 像素的纹理:
- **宽度**: 256 (对应 0-255 的输入值)
- **高度**: 4 (对应 A、R、G、B 四个通道)
- **行 0**: Alpha 通道查找表
- **行 1**: 红色通道查找表
- **行 2**: 绿色通道查找表
- **行 3**: 蓝色通道查找表

### 着色器代码生成

`Impl::emitCode` 生成的 GLSL 代码逻辑:

```glsl
// 1. 获取输入颜色并转换为 0-255 范围
half4 coord = 255 * unpremul(inputColor) + 0.5;

// 2. 查找每个通道的映射值
half a_mapped = texture(lut, half2(coord.a, 0.5)).a;  // 行 0
half r_mapped = texture(lut, half2(coord.r, 1.5)).a;  // 行 1
half g_mapped = texture(lut, half2(coord.g, 2.5)).a;  // 行 2
half b_mapped = texture(lut, half2(coord.b, 3.5)).a;  // 行 3

// 3. 组合映射后的颜色
half4 color = half4(r_mapped, g_mapped, b_mapped, 1);

// 4. 应用映射后的 alpha
return color * a_mapped;
```

### unpremul 预乘处理

输入颜色需要先解除预乘:
- 将预乘 alpha 格式转换为直通 alpha
- 确保查找表正确应用到原始颜色值
- 最后重新应用 alpha(通过乘法)

### 坐标偏移 0.5

查找坐标加 0.5 是为了正确采样:
- 纹理坐标 0.0 对应像素中心 0.5
- 确保整数值映射到正确的纹理像素
- 避免插值导致的精度问题

### 纹理采样优化

使用 Y 坐标区分通道:
- `coord.a, 0.5` - Alpha 通道(第 0 行中心)
- `coord.r, 1.5` - 红色通道(第 1 行中心)
- `coord.g, 2.5` - 绿色通道(第 2 行中心)
- `coord.b, 3.5` - 蓝色通道(第 3 行中心)

这允许单次纹理绑定完成所有通道查找。

### 子处理器注册

构造函数注册两个子处理器:
1. **纹理效果**: 使用显式采样(`SkSL::SampleUsage::Explicit`)
2. **输入处理器**: 使用默认采样

显式采样允许为每个通道指定不同的纹理坐标。

### 优化标志

构造时使用 `kNone_OptimizationFlags`:
- 不声明保留不透明度
- 不声明兼容覆盖率
- 查找表可能产生任意输出,无法预测优化

### 相等性比较

`onIsEqual` 总是返回 `true`:
- 所有 `ColorTableEffect` 实例功能相同
- 查找表数据存储在纹理中,不影响程序本身
- 简化了着色器缓存键生成

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrFragmentProcessor` | 片段处理器基类 |
| `GrTextureEffect` | 纹理采样子处理器 |
| `GrMippedBitmap` | 查找表位图封装 |
| `GrSurfaceProxyView` | 纹理视图 |
| `GrGLSLFragmentShaderBuilder` | 着色器代码生成 |
| `SkColorFilter` | 颜色过滤器抽象 |
| `GrRecordingContext` | GPU 上下文 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrFragmentProcessors` | 通过工厂创建颜色表效果 |
| `SkColorFilter` | `TableARGB` 颜色过滤器使用 |
| 图像处理管线 | 应用颜色校正和映射 |

## 设计模式与设计决策

### 组合模式

通过子处理器组合实现效果:
- 输入处理器提供源颜色
- 纹理效果提供查找表采样
- 主处理器协调两者生成最终着色器

### 纹理查找优化

将 4 个独立的 1D 查找表合并为单个 2D 纹理:
- 减少纹理绑定数量(1 个而非 4 个)
- 利用 2D 纹理缓存
- 简化着色器逻辑

### 解耦的测试创建

提供 `TestCreate` 方法用于随机测试:
- 生成随机查找表配置
- 测试各种通道组合
- 验证效果的正确性

### 显式采样模式

对纹理效果使用显式采样:
- 允许为每个通道指定不同坐标
- 避免隐式坐标传递的限制
- 提供最大的灵活性

### 无优化声明

不声明任何优化标志:
- 查找表可能改变任意颜色属性
- 避免错误的优化假设
- 简化实现但可能牺牲性能

## 性能考量

### 纹理查找次数

每个像素执行 4 次纹理查找:
- Alpha、红、绿、蓝各一次
- 现代 GPU 的纹理单元可并行处理
- 相比 CPU 实现仍有显著加速

### 纹理缓存效率

256x4 查找表非常小:
- 总大小仅 4KB(RGBA8 格式)
- 完全适合 GPU 纹理缓存
- 查找延迟极低

### unpremul 开销

解除预乘需要除法操作:
- GPU 上的除法相对昂贵
- 但对于查找表语义是必需的
- 每像素仅执行一次

### 显式采样的灵活性

显式坐标传递的成本:
- 增加 varying 数据传输
- 但提供必要的灵活性
- 对于查找表效果是合理权衡

### 着色器复杂度

生成的着色器相对简单:
- 主要是纹理采样和算术运算
- 无分支或复杂控制流
- GPU 执行效率高

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 基类 | 片段处理器抽象 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 依赖 | 纹理采样效果 |
| `src/gpu/ganesh/image/GrMippedBitmap.h` | 依赖 | 位图封装 |
| `src/gpu/ganesh/GrFragmentProcessors.h` | 被使用 | 效果工厂 |
| `include/effects/SkColorFilterImageFilter.h` | 相关 | 颜色过滤器 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 着色器构建器 |
