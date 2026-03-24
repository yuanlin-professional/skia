# SkColorSpace

> 源文件: include/core/SkColorSpace.h, src/core/SkColorSpace.cpp

## 概述

`SkColorSpace` 表示色彩空间,定义了颜色的数值表示方式。它封装了传递函数(transfer function)和色域变换矩阵(gamut transform),用于在不同色彩空间之间转换颜色。该类是 Skia 色彩管理系统的核心,支持 SDR 和 HDR 色彩空间,包括 sRGB、Display P3、Rec2020、PQ 和 HLG 等标准。

## 架构位置

`SkColorSpace` 是 Skia 核心公共 API 的一部分,位于色彩管理层。它与 skcms(Skia 色彩管理系统)库紧密集成,为图像、表面、着色器等所有需要色彩表示的组件提供基础设施。该类采用引用计数管理(`SkNVRefCnt`),支持高效的共享和复制。

## 主要类与结构体

### SkColorSpace

| 特性 | 说明 |
|------|------|
| 继承关系 | 继承自 `SkNVRefCnt<SkColorSpace>` |
| 线程安全 | 不可变对象,线程安全 |
| 内存管理 | 引用计数 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTransferFn` | `skcms_TransferFunction` | 传递函数(EOTF,电光转换函数) |
| `fToXYZD50` | `skcms_Matrix3x3` | 到 XYZ D50 的色域变换矩阵 |
| `fTransferFnHash` | `uint32_t` | 传递函数的哈希值 |
| `fToXYZD50Hash` | `uint32_t` | 色域矩阵的哈希值 |
| `fInvTransferFn` | `skcms_TransferFunction` (mutable) | 逆传递函数(OETF) |
| `fFromXYZD50` | `skcms_Matrix3x3` (mutable) | 从 XYZ D50 的逆矩阵 |
| `fLazyDstFieldsOnce` | `SkOnce` (mutable) | 惰性初始化标志 |

### SkColorSpacePrimaries

表示色域的原色和白点:

| 成员 | 说明 |
|------|------|
| `fRX, fRY` | 红色原色的 xy 色度坐标 |
| `fGX, fGY` | 绿色原色的 xy 色度坐标 |
| `fBX, fBY` | 蓝色原色的 xy 色度坐标 |
| `fWX, fWY` | 白点的 xy 色度坐标 |

**方法:**
```cpp
bool toXYZD50(skcms_Matrix3x3* toXYZD50) const;
```
- 将原色转换为 toXYZD50 矩阵

## 公共 API 函数

### 创建方法

```cpp
static sk_sp<SkColorSpace> MakeSRGB();
static sk_sp<SkColorSpace> MakeSRGBLinear();
```
- 创建常用的 sRGB 和线性 sRGB 色彩空间
- 使用单例优化,返回相同实例

```cpp
static sk_sp<SkColorSpace> MakeRGB(const skcms_TransferFunction& transferFn,
                                   const skcms_Matrix3x3& toXYZ);
```
- 从传递函数和色域矩阵创建自定义色彩空间
- 自动识别并返回常见色彩空间的单例

```cpp
static sk_sp<SkColorSpace> MakeCICP(SkNamedPrimaries::CicpId color_primaries,
                                    SkNamedTransferFn::CicpId transfer_characteristics);
```
- 从 ITU-T H.273 标准的 CICP 代码点创建
- 支持标准化的色彩空间表示

```cpp
static sk_sp<SkColorSpace> Make(const skcms_ICCProfile&);
```
- 从 ICC 配置文件创建
- 支持从图像嵌入的配置文件创建

### 查询方法

```cpp
bool gammaCloseToSRGB() const;
bool gammaIsLinear() const;
```
- 检查传递函数是否接近 sRGB 或线性

```cpp
bool isNumericalTransferFn(skcms_TransferFunction* fn) const;
```
- 检查传递函数是否可表示为 7 参数方程
- PQ 和 HLG 返回 false

```cpp
bool toXYZD50(skcms_Matrix3x3* toXYZD50) const;
```
- 获取色域变换矩阵

```cpp
uint32_t toXYZD50Hash() const;
uint32_t transferFnHash() const;
uint64_t hash() const;
```
- 获取哈希值用于快速比较

```cpp
bool isSRGB() const;
```
- 检查是否为 sRGB 色彩空间(指针比较)

### 变换方法

```cpp
void transferFn(skcms_TransferFunction* fn) const;
void invTransferFn(skcms_TransferFunction* fn) const;
```
- 获取传递函数和逆传递函数

```cpp
void gamutTransformTo(const SkColorSpace* dst, skcms_Matrix3x3* src_to_dst) const;
```
- 计算到目标色彩空间的色域变换矩阵

```cpp
sk_sp<SkColorSpace> makeLinearGamma() const;
sk_sp<SkColorSpace> makeSRGBGamma() const;
```
- 创建具有相同色域但不同传递函数的色彩空间

```cpp
sk_sp<SkColorSpace> makeColorSpin() const;
```
- 创建旋转原色的色彩空间(用于测试)
- RGB → GBR

### 序列化

```cpp
sk_sp<SkData> serialize() const;
size_t writeToMemory(void* memory) const;
static sk_sp<SkColorSpace> Deserialize(const void* data, size_t length);
```
- 序列化和反序列化色彩空间

```cpp
void toProfile(skcms_ICCProfile* profile) const;
```
- 转换为 ICC 配置文件

### 比较

```cpp
static bool Equals(const SkColorSpace*, const SkColorSpace*);
```
- 深度比较两个色彩空间
- 处理 null 指针情况

## 内部实现细节

### 哈希值计算

使用 `SkChecksum::Hash32` 计算哈希值:
```cpp
fTransferFnHash = SkChecksum::Hash32(&fTransferFn, 7*sizeof(float));
fToXYZD50Hash = SkChecksum::Hash32(&fToXYZD50, 9*sizeof(float));
```

组合哈希用于快速相等性检查:
```cpp
uint64_t hash() const {
    return (uint64_t)fTransferFnHash << 32 | fToXYZD50Hash;
}
```

### 单例模式

常用色彩空间使用单例:
```cpp
SkColorSpace* sk_srgb_singleton() {
    static SkColorSpace* cs = SkColorSpaceSingletonFactory::Make(
        SkNamedTransferFn::kSRGB, SkNamedGamut::kSRGB);
    return cs;
}
```

### 惰性计算

逆传递函数和逆矩阵延迟计算:
```cpp
void SkColorSpace::computeLazyDstFields() const {
    fLazyDstFieldsOnce([this] {
        skcms_Matrix3x3_invert(&fToXYZD50, &fFromXYZD50);
        skcms_TransferFunction_invert(&fTransferFn, &fInvTransferFn);
    });
}
```

### CICP 支持

支持 ITU-T H.273 标准的色彩空间参数:

**命名空间 SkNamedPrimaries:**
- 定义标准原色(Rec709, Rec2020, DisplayP3 等)
- 提供 CICP ID 枚举
- 实现 CICP 到矩阵的转换

**命名空间 SkNamedTransferFn:**
- 定义标准传递函数(sRGB, Linear, PQ, HLG 等)
- 提供 CICP ID 枚举
- 实现 CICP 到传递函数的转换

### ICC 配置文件处理

`Make(const skcms_ICCProfile&)` 实现复杂的配置文件解析逻辑:
1. 优先使用 CICP 标签(如果存在且有效)
2. 回退到 toXYZD50 和 trc 标签
3. 对于表格形式的 trc,尝试近似为标准函数
4. 检测并返回 sRGB 单例

### 近似比较

使用容差比较浮点值:
```cpp
static inline bool color_space_almost_equal(float a, float b) {
    return SkTAbs(a - b) < 0.01f;
}

static inline bool transfer_fn_almost_equal(float a, float b) {
    return SkTAbs(a - b) < 0.001f;
}
```

传递函数使用更严格的容差(0.001),因为 ICC 提供 16 位精度。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `skcms` | 色彩管理核心库 |
| `SkRefCnt` | 引用计数 |
| `SkData` | 序列化数据存储 |
| `SkChecksum` | 哈希值计算 |
| `SkOnce` | 线程安全的惰性初始化 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkImage` | 包含色彩空间信息 |
| `SkSurface` | 定义渲染目标的色彩空间 |
| `SkColorFilter` | 色彩空间转换 |
| `SkShader` | 着色器的色彩空间 |
| `SkCanvas` | 绘制时的色彩空间处理 |
| GPU 后端 | GPU 色彩空间转换 |

## 设计模式与设计决策

### 不可变值对象

色彩空间一旦创建就不可变:
- 线程安全
- 可以安全共享
- 哈希值可以缓存

### 单例模式

常用色彩空间(sRGB, sRGB Linear)使用单例:
- 减少内存开销
- 快速指针比较
- 避免重复创建

### 惰性初始化

逆函数和逆矩阵延迟计算:
- 大多数用途不需要这些值
- 使用 `SkOnce` 保证线程安全
- 计算成本较高,仅在需要时执行

### 标准化表示

内部始终使用 D50 白点:
- 简化色彩空间转换
- 符合 ICC 标准
- 所有矩阵都是 toXYZD50 形式

## 性能考量

### 哈希缓存

哈希值在构造时计算并缓存:
- 快速相等性检查
- 避免重复计算
- 64 位哈希(两个 32 位哈希组合)

### 单例优化

常见色彩空间使用单例:
- 指针比较代替深度比较
- `isSRGB()` 仅进行指针比较

### 矩阵近似

`MakeRGB` 检测近似相等的矩阵并返回标准单例:
```cpp
if (is_almost_srgb(transferFn) && xyz_almost_equal(toXYZ, SkNamedGamut::kSRGB)) {
    return SkColorSpace::MakeSRGB();
}
```

### 调试验证

在调试模式下验证哈希碰撞:
```cpp
#ifdef SK_DEBUG
    SkASSERT(0 == memcmp(&srcM, &dstM, 9*sizeof(float)) && "Hash collision");
#endif
```

### 序列化优化

序列化格式紧凑:
- 简单的头部(4 字节)
- 7 个浮点数(传递函数)
- 9 个浮点数(矩阵)
- 总共 68 字节

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `modules/skcms/skcms.h` | 核心依赖 | 色彩管理函数 |
| `include/core/SkRefCnt.h` | 基类 | 引用计数 |
| `include/core/SkData.h` | 依赖 | 序列化数据 |
| `src/core/SkColorSpacePriv.h` | 私有 API | 内部辅助函数 |
| `src/core/SkChecksum.h` | 依赖 | 哈希计算 |
| `include/private/base/SkOnce.h` | 依赖 | 惰性初始化 |
| `include/core/SkImage.h` | 使用者 | 图像色彩空间 |
| `include/core/SkSurface.h` | 使用者 | 表面色彩空间 |
