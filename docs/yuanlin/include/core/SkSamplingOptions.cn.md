# SkSamplingOptions

> 源文件: `include/core/SkSamplingOptions.h`

## 概述
SkSamplingOptions 封装了图像采样和过滤参数，用于控制图像缩放、旋转和变换时的质量与性能权衡。它统一了 Skia 中各种采样策略，支持最近邻、线性、立方重采样和各向异性过滤等多种模式。

## 架构位置
位于 Skia 核心模块 (`include/core`)，作为图像渲染子系统的基础配置类型。被 SkCanvas、SkShader、SkImage 等图像处理 API 广泛使用，是控制渲染质量的核心接口。

## 主要类与结构体

### SkCubicResampler
```cpp
struct SkCubicResampler {
    float B, C;

    static constexpr SkCubicResampler Mitchell() { return {1/3.0f, 1/3.0f}; }
    static constexpr SkCubicResampler CatmullRom() { return {0.0f, 1/2.0f}; }
};
```

**职责**: 定义立方重采样滤波器的参数。

**数学基础**: Mitchell-Netravali 滤波器族，通过调整 B 和 C 参数控制锐化/模糊特性。

**经典配置**:
- **Mitchell (1/3, 1/3)**: 平衡锐度和平滑度，视觉质量优秀
- **Catmull-Rom (0, 1/2)**: 更锐利，保留更多细节

### SkSamplingOptions
主结构体，包含所有采样参数。

**关键成员变量**:
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| maxAniso | const int | 0 | 最大各向异性度（0 = 禁用） |
| useCubic | const bool | false | 是否使用立方重采样 |
| cubic | const SkCubicResampler | {0, 0} | 立方滤波器参数 |
| filter | const SkFilterMode | kNearest | 过滤模式 |
| mipmap | const SkMipmapMode | kNone | Mipmap 使用策略 |

## 枚举类型

### SkFilterMode
```cpp
enum class SkFilterMode {
    kNearest,  // 最近邻采样
    kLinear,   // 双线性插值
    kLast = kLinear,
};
```

**模式说明**:
- **kNearest**: 选择最近的像素，速度最快，质量最低
- **kLinear**: 在 2x2 像素间双线性插值，质量和性能平衡

### SkMipmapMode
```cpp
enum class SkMipmapMode {
    kNone,     // 忽略 mipmap
    kNearest,  // 选择最近的 mipmap 层级
    kLinear,   // 在两个最近层级间插值（三线性过滤）
    kLast = kLinear,
};
```

**Mipmap 策略**:
- **kNone**: 总是从基础层采样
- **kNearest**: 根据缩放级别选择一个 mipmap
- **kLinear**: 三线性过滤，在两个 mipmap 层间平滑过渡

## 公共 API 函数

### 构造函数

#### 默认构造
```cpp
constexpr SkSamplingOptions() = default;
```
- **默认行为**: kNearest 过滤，无 mipmap，最低质量最高性能

#### 过滤模式构造
```cpp
constexpr SkSamplingOptions(SkFilterMode fm)
constexpr SkSamplingOptions(SkFilterMode fm, SkMipmapMode mm)
```
- **用途**: 快速创建标准过滤配置
- **隐式转换**: 单参数构造函数支持隐式转换

#### 立方重采样构造
```cpp
constexpr SkSamplingOptions(const SkCubicResampler& c)
```
- **用途**: 使用立方滤波器，高质量缩放
- **自动设置**: useCubic = true, cubic = c

### 静态工厂方法

#### `Aniso(int maxAniso)`
```cpp
static constexpr SkSamplingOptions Aniso(int maxAniso)
```
- **功能**: 创建各向异性过滤配置
- **参数**: maxAniso - 最大各向异性度（通常 2、4、8、16）
- **自动限制**: 最小值为 1
- **用途**: 处理透视变换下的纹理采样

### 运算符重载

#### 相等比较
```cpp
bool operator==(const SkSamplingOptions& other) const
bool operator!=(const SkSamplingOptions& other) const
```
- **实现**: 比较所有成员变量
- **注意**: 浮点比较使用精确相等（非近似）

### 查询函数

#### `isAniso()`
```cpp
bool isAniso() const { return maxAniso != 0; }
```
- **功能**: 检查是否启用各向异性过滤

## 采样模式详解

### 最近邻采样 (Nearest Neighbor)
```cpp
SkSamplingOptions nearest;  // 默认构造
// 或
SkSamplingOptions nearest(SkFilterMode::kNearest);
```
- **算法**: 选择最近的像素值
- **优点**: 速度最快，像素艺术风格
- **缺点**: 锯齿明显，缩放质量差

### 双线性过滤 (Bilinear)
```cpp
SkSamplingOptions bilinear(SkFilterMode::kLinear);
```
- **算法**: 2x2 像素的加权平均
- **优点**: 平滑，性能良好
- **缺点**: 缩小时可能产生摩尔纹

### 三线性过滤 (Trilinear)
```cpp
SkSamplingOptions trilinear(SkFilterMode::kLinear, SkMipmapMode::kLinear);
```
- **算法**: 双线性 + mipmap 层间插值
- **优点**: 缩小质量优秀，无摩尔纹
- **要求**: 图像必须有 mipmap

### 立方重采样 (Cubic)
```cpp
SkSamplingOptions mitchell(SkCubicResampler::Mitchell());
SkSamplingOptions catmullRom(SkCubicResampler::CatmullRom());
```
- **算法**: 4x4 像素的三次多项式插值
- **优点**: 质量最高，放大效果优秀
- **缺点**: 性能开销较大

### 各向异性过滤 (Anisotropic)
```cpp
SkSamplingOptions aniso = SkSamplingOptions::Aniso(8);
```
- **算法**: 根据纹理变形方向调整采样核形状
- **优点**: 透视变换下保持清晰
- **典型值**: 2、4、8、16（越高质量越好）

## 使用场景

### 图像绘制
```cpp
canvas->drawImage(image, x, y,
    SkSamplingOptions(SkFilterMode::kLinear), paint);
```

### 着色器创建
```cpp
auto shader = image->makeShader(
    SkTileMode::kClamp, SkTileMode::kClamp,
    SkSamplingOptions(SkCubicResampler::Mitchell())
);
```

### 位图缩放
```cpp
// 高质量缩略图生成
bitmap.pixmap().scalePixels(
    dstPixmap,
    SkSamplingOptions(SkCubicResampler::Mitchell())
);
```

### 性能与质量权衡
```cpp
// 实时渲染：快速模式
SkSamplingOptions realtime(SkFilterMode::kLinear);

// 静态内容：高质量模式
SkSamplingOptions highQuality(SkCubicResampler::Mitchell());

// 远景纹理：各向异性
SkSamplingOptions perspective = SkSamplingOptions::Aniso(16);
```

## 内部实现细节

### 私有构造函数
```cpp
private:
    constexpr SkSamplingOptions(int maxAniso) : maxAniso(maxAniso) {}
```
- **用途**: 支持 Aniso() 工厂方法
- **封装**: 防止直接创建无效的各向异性配置

### 成员变量顺序
成员变量的声明顺序经过优化：
- 整数在前（maxAniso）
- 布尔值（useCubic）
- 结构体（cubic）
- 枚举（filter, mipmap）

这种排列可能有助于内存对齐和缓存效率。

### 常量性设计
所有成员变量标记为 `const`：
- 不可变对象，线程安全
- 编译器可优化
- 语义清晰：采样选项不应在创建后修改

## 数学背景

### Mitchell-Netravali 滤波器
论文来源："Reconstruction Filters in Computer Graphics" (1988)

**公式**（简化）:
```
k(x) = 当 |x| < 1:
         (12 - 9B - 6C)|x|³ + (-18 + 12B + 6C)|x|² + (6 - 2B)
       当 1 ≤ |x| < 2:
         (-B - 6C)|x|³ + (6B + 30C)|x|² + (-12B - 48C)|x| + (8B + 24C)
```

**参数影响**:
- **B 增大**: 更模糊，减少振铃
- **C 增大**: 更锐利，可能产生过冲

### 各向异性过滤原理
标准采样假设采样核是圆形的，但透视变换会使纹理变形为椭圆。各向异性过滤使用椭圆形采样核匹配变形。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `<algorithm>` | std::max 用于 Aniso() |
| `<new>` | placement new（赋值运算符） |

### 被依赖的模块
- **SkCanvas**: 所有绘图函数的采样参数
- **SkImage**: makeShader() 等方法
- **SkShader**: 图像着色器
- **SkSurface**: draw() 方法

## 设计模式与设计决策

### 值语义
SkSamplingOptions 是轻量级值类型：
- 按值传递（约 16 字节）
- 不涉及所有权
- 线程安全（不可变）

### 隐式转换支持
单参数构造函数允许隐式转换：
```cpp
void drawImage(SkImage*, SkSamplingOptions);

// 可以这样调用
drawImage(img, SkFilterMode::kLinear);  // 隐式转换
```

这提高了 API 的易用性。

### 工厂方法命名
- `Mitchell()`, `CatmullRom()`: 命名滤波器，语义清晰
- `Aniso()`: 特殊构造，需要参数验证

### 命名约定变更
注释中的"赋值运算符注释"提到"pedantic no-op"，表明这是为了满足某些编译器或代码规范的要求。

## 性能考量

### 性能排序（快到慢）
1. Nearest (最快)
2. Linear
3. Linear + Nearest Mipmap
4. Linear + Linear Mipmap (Trilinear)
5. Cubic (最慢，CPU)
6. Anisotropic (取决于硬件）

### GPU 加速
- Nearest, Linear, Trilinear: 通常有硬件支持
- Cubic: 可能需要 shader 实现
- Anisotropic: 现代 GPU 有硬件支持

### 内存占用
- Mipmap 需要额外 1/3 内存
- 各向异性过滤无额外内存需求

## 历史演进

### kHigh_SkFilterQuality 替代
注释提到 Mitchell 是"Historic default for kHigh_SkFilterQuality"，表明 Skia 曾使用旧的质量枚举系统，现已被更精细的 SkSamplingOptions 取代。

### C++11 特性
- constexpr 构造函数
- 默认拷贝构造
- placement new 在赋值运算符中的使用

## 最佳实践

### 根据场景选择
- **UI 图标**: Linear（平滑但保持性能）
- **照片放大**: Cubic Mitchell（高质量）
- **像素艺术**: Nearest（保持像素边界）
- **3D 纹理**: Trilinear + Anisotropic（处理透视）

### 性能优化
```cpp
// 缓存常用配置
static const SkSamplingOptions kLinear(SkFilterMode::kLinear);
static const SkSamplingOptions kMitchell(SkCubicResampler::Mitchell());

// 避免重复构造
canvas->drawImage(img, x, y, kLinear, paint);
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkCanvas.h` | 使用 SkSamplingOptions 作为参数 |
| `include/core/SkImage.h` | makeShader() 等方法 |
| `include/core/SkShader.h` | 图像着色器使用 |
| `include/core/SkSurface.h` | draw() 方法参数 |
| Mitchell-Netravali 论文 | 数学基础 |
