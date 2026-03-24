# SkColorSpacePriv

> 源文件: src/core/SkColorSpacePriv.h

## 概述

`SkColorSpacePriv.h` 提供 `SkColorSpace` 的私有辅助函数和工具,包括传递函数和色域的近似比较、标准色彩空间的识别、CICP 代码点的转换,以及单例色彩空间的访问。这些工具主要用于 Skia 内部的色彩空间优化和标准化,不属于公共 API。

## 架构位置

`SkColorSpacePriv.h` 位于 Skia 核心层(src/core),是私有实现头文件。它为 `SkColorSpace` 提供内部辅助功能,被色彩空间创建、转换和优化代码使用。该文件定义了内部使用的比较阈值、标准化逻辑和单例访问方法。

## 主要类与结构体

该文件主要定义内联函数、常量和命名空间函数,不定义类。

## 公共 API 函数

### 近似比较

**色域近似相等:**
```cpp
static inline bool color_space_almost_equal(float a, float b) {
    return SkTAbs(a - b) < 0.01f;
}
```
- 容差: 0.01
- 用于色域矩阵元素比较
- 考虑浮点运算的不精确性

**传递函数近似相等:**
```cpp
static inline bool transfer_fn_almost_equal(float a, float b) {
    return SkTAbs(a - b) < 0.001f;
}
```
- 容差: 0.001(更严格)
- 用于传递函数参数比较
- ICC 格式提供 16 位精度,需要更严格的容差

### 标准传递函数识别

**sRGB 检测:**
```cpp
static inline bool is_almost_srgb(const skcms_TransferFunction& coeffs);
```
- 检查传递函数是否近似 sRGB
- 比较所有 7 个参数(a, b, c, d, e, f, g)
- 用于返回 sRGB 单例优化

**2.2 伽马检测:**
```cpp
static inline bool is_almost_2dot2(const skcms_TransferFunction& coeffs);
```
- 检查传递函数是否近似 2.2 次幂
- 标准形式: `y = x^2.2`
- 条件:
  - `a ≈ 1.0`
  - `b ≈ 0.0`
  - `e ≈ 0.0`
  - `g ≈ 2.2`
  - `d ≤ 0.0`

**线性检测:**
```cpp
static inline bool is_almost_linear(const skcms_TransferFunction& coeffs);
```
- 检查传递函数是否近似线性
- 支持两种形式:
  1. **幂函数形式**: `y = x^1.0`
     - `a ≈ 1.0, b ≈ 0.0, e ≈ 0.0, g ≈ 1.0, d ≤ 0.0`
  2. **线性函数形式**: `y = 1.0 * x`
     - `c ≈ 1.0, f ≈ 0.0, d ≥ 1.0`

### 单例访问

```cpp
SkColorSpace* sk_srgb_singleton();
SkColorSpace* sk_srgb_linear_singleton();
```

**功能:**
- 返回常用色彩空间的单例实例
- 无需引用计数操作
- 如果引用计数,必须成对 ref/unref

**注意事项:**
- 返回原始指针,不增加引用计数
- 单例生命周期由 Skia 管理
- 线程安全(静态初始化)

**使用场景:**
```cpp
if (cs == sk_srgb_singleton()) {
    // 快速指针比较,无需深度比较
}
```

### CICP 转换

**命名空间 SkNamedPrimaries:**
```cpp
bool GetCicp(CicpId primaries, skcms_Matrix3x3& toXYZD50);
```
- 从 CICP ID 获取色域矩阵
- 支持标准原色(Rec709, Rec2020, DisplayP3 等)
- 返回 false 表示不支持的 ID

**命名空间 SkNamedTransferFn:**
```cpp
bool GetCicp(CicpId transfer_characteristics, skcms_TransferFunction& trfn);
```
- 从 CICP ID 获取传递函数
- 支持标准传递函数(sRGB, Linear, PQ, HLG 等)
- 返回 false 表示不支持的 ID

## 内部实现细节

### 测试用窄色域

```cpp
static constexpr skcms_Matrix3x3 gNarrow_toXYZD50 = {{
    { 0.190974f,  0.404865f,  0.368380f },
    { 0.114746f,  0.582937f,  0.302318f },
    { 0.032925f,  0.153615f,  0.638669f },
}};
```

**用途:**
- 比 sRGB 更窄的色域
- 用于测试色域转换边界情况
- 验证色域映射算法

### 容差选择

不同容差的原因:

| 类型 | 容差 | 原因 |
|------|------|------|
| 色域矩阵 | 0.01 | ICC 固定点精度 + 运算误差 |
| 传递函数 | 0.001 | ICC 提供 16 位分数精度 |

### 近似识别的意义

自动识别标准色彩空间的好处:

1. **返回单例**: 减少内存使用
2. **快速比较**: 指针比较代替深度比较
3. **优化路径**: 为常见色彩空间提供快速转换
4. **规范化**: 统一表示略有差异的色彩空间

### 传递函数参数

skcms 传递函数的 7 参数形式:
```cpp
struct skcms_TransferFunction {
    float g, a, b, c, d, e, f;
};
```

**分段函数:**
```
if x < d:
    y = c * x + f
else:
    y = (a * x + b)^g + e
```

**常见形式:**
- **sRGB**: 两段,线性段 + 幂函数段
- **线性**: `g=1, a=1, b=0, e=0` 或 `c=1, f=0, d≥1`
- **2.2 伽马**: `g=2.2, a=1, b=0, e=0, d≤0`

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkColorSpace` | 扩展其功能 |
| `skcms` | 色彩管理数据结构 |
| `SkTemplates` | 模板工具(`SkTAbs`) |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkColorSpace.cpp` | 使用这些辅助函数 |
| `SkColorSpaceXformSteps.cpp` | 访问单例 |
| ICC 配置文件解析器 | 识别标准色彩空间 |
| 图像解码器 | 标准化色彩空间 |

## 设计模式与设计决策

### 内联辅助函数

所有比较函数都是内联的:
- 在性能关键路径上使用
- 避免函数调用开销
- 允许编译器优化

### 单例模式

常用色彩空间使用单例:
- 减少重复创建
- 快速指针比较
- 线程安全(静态局部变量)

### 宽松比较

使用容差比较而不是精确相等:
- 处理浮点运算误差
- 兼容不同来源的色彩空间数据
- 自动规范化到标准表示

### 命名空间扩展

在 `SkNamedPrimaries` 和 `SkNamedTransferFn` 命名空间中添加函数:
- 保持 API 组织清晰
- 避免全局命名空间污染
- 与公共 API 结构一致

## 性能考量

### 早期识别

在色彩空间创建时就识别标准形式:
- 避免运行时重复比较
- 缓存识别结果(通过返回单例)
- 优化后续操作

### 指针比较

单例允许 O(1) 的相等性检查:
```cpp
bool SkColorSpace::isSRGB() const {
    return sk_srgb_singleton() == this;
}
```

### 避免深度比较

通过近似识别减少需要深度比较的情况:
- 大多数色彩空间可以规范化到单例
- 减少哈希碰撞检查
- 简化转换矩阵计算

### 惰性计算

单例使用静态局部变量惰性初始化:
```cpp
SkColorSpace* sk_srgb_singleton() {
    static SkColorSpace* cs = ...;
    return cs;
}
```
- 仅在首次使用时创建
- 线程安全(C++11 保证)
- 程序生命周期内存在

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColorSpace.h` | 公共 API | 色彩空间公共接口 |
| `src/core/SkColorSpace.cpp` | 实现 | 使用私有 API |
| `modules/skcms/skcms.h` | 依赖 | 色彩管理数据结构 |
| `include/private/base/SkTemplates.h` | 依赖 | 模板工具 |
| `src/core/SkColorSpaceXformSteps.cpp` | 使用者 | 访问单例 |
| ICC 配置文件解析器 | 使用者 | 标准化色彩空间 |
