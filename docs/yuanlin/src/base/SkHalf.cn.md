# SkHalf - 半精度浮点数
> 源文件: `src/base/SkHalf.h`, `src/base/SkHalf.cpp`

## 概述
SkHalf 模块提供了半精度浮点数（16位浮点数，FP16）与单精度浮点数（32位浮点数，float）之间的转换功能。半精度浮点数采用 IEEE 754 标准格式，由 1 位符号位、5 位指数位和 10 位尾数位组成，主要用于图形处理中的内存优化和数据存储场景。

## 架构位置
SkHalf 位于 Skia 基础模块（src/base）中，属于底层数值类型支持层。它为上层的颜色处理、纹理存储、GPU 数据传输等模块提供半精度浮点数的转换能力，在需要节省内存和带宽的场景中发挥重要作用。

## 主要类与结构体

### SkHalf (类型别名)
```cpp
using SkHalf = uint16_t;
```

**职责**: 半精度浮点数的存储表示类型

**特点**:
- 仅用于存储，不用于直接运算
- 使用 uint16_t 作为底层类型，避免类型转换问题
- IEEE 754 半精度格式：1 位符号 + 5 位指数 + 10 位尾数

**预定义常量**:
| 常量名 | 值 | 含义 |
|--------|-----|------|
| SK_HalfNaN | 0x7c01 | NaN 值（非所有可能的 NaN） |
| SK_HalfInfinity | 0x7c00 | 正无穷大 |
| SK_HalfMin | 0x0400 | 最小正规格化数（2^-14） |
| SK_HalfMax | 0x7bff | 最大正规格化数（65504） |
| SK_HalfEpsilon | 0x1400 | 机器精度（2^-10） |
| SK_Half1 | 0x3C00 | 数值 1.0 |

## 公共 API 函数

### `float SkHalfToFloat(SkHalf h)`
- **功能**: 将半精度浮点数转换为单精度浮点数
- **参数**: h - 半精度浮点数（16位）
- **返回值**: 对应的单精度浮点数（32位）
- **实现细节**: 使用 skvx 向量化库的 `from_half` 函数进行转换，单个元素的向量化调用会被编译器优化为标量操作

### `SkHalf SkFloatToHalf(float f)`
- **功能**: 将单精度浮点数转换为半精度浮点数
- **参数**: f - 单精度浮点数（32位）
- **返回值**: 对应的半精度浮点数（16位）
- **实现细节**:
  - 特殊处理 NaN：所有 NaN 都转换为标准的 SK_HalfNaN
  - 对于非 NaN 值，使用 skvx 的 `to_half` 函数
  - 不同于 skvx::to_half，此函数正确处理 float NaN -> half NaN 的转换

## 内部实现细节

### 为何在 CPP 文件中实现
注释明确指出：
```
// NOTE: These are defined within the CPP compilation unit so that they are
// not inlined everywhere and increase code size.
```

这两个函数定义在 .cpp 文件中而非头文件内联，是为了：
1. **减少代码膨胀**: 避免在每个调用点都内联展开
2. **编译单元隔离**: 降低编译依赖
3. **性能关键路径优化**: 性能关键代码通常已直接使用 skvx 向量化接口，这些标量接口主要用于非性能关键路径

### 向量化实现策略
```cpp
SkHalf SkFloatToHalf(float f) {
    if (std::isnan(f)) {
        return SK_HalfNaN;
    } else {
        return to_half(skvx::Vec<1,float>(f))[0];
    }
}
```

使用长度为 1 的向量（`skvx::Vec<1,float>`）来调用向量化函数，这看似奇怪，但有以下原因：
1. 复用 skvx 的向量转换实现，避免重复代码
2. 编译器会将单元素向量优化为标量操作
3. 统一的接口设计，向量和标量使用相同的转换逻辑

### NaN 处理策略
IEEE 754 标准中有多种 NaN 表示（尾数非零的任意值），但 Skia 选择统一映射到 `SK_HalfNaN (0x7c01)`：
- **一致性**: 保证所有 NaN 有相同的位模式
- **可预测性**: 简化调试和测试
- **兼容性**: 某些硬件对不同 NaN 位模式处理不一致

### 精度损失
从 float (23 bits 尾数) 转换到 half (10 bits 尾数) 会发生精度损失：
- 损失约 13 bits 的尾数精度
- 指数范围从 [-126, 127] 缩小到 [-14, 15]
- 溢出值会转换为 Infinity
- 下溢值会转换为 0 或次正规数（subnormal）

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| src/base/SkVx.h | SIMD 向量化数学库，提供 from_half 和 to_half |
| include/private/base/SkFloatingPoint.h | 浮点数工具（头文件引用） |
| std::isnan | 标准库 NaN 检测函数 |

### 被依赖的模块
- 纹理处理模块（支持 FP16 纹理格式）
- 颜色空间转换（HDR 颜色处理）
- GPU 数据上传（减少带宽）
- 图像编解码器（某些格式使用 FP16）
- 着色器数据打包

## 设计模式与设计决策

### 类型别名而非类封装
使用 `using SkHalf = uint16_t` 而非定义独立的类：
- **优点**:
  - 与 C 和底层 API 兼容
  - 可以直接用于数组和内存操作
  - 避免类型转换开销
- **缺点**:
  - 失去类型安全性（可能与普通 uint16_t 混淆）
  - 无法重载运算符

这个决策体现了 Skia 重视性能和内存布局的特点。

### 仅用于存储的设计原则
半精度浮点数在 Skia 中被定位为"存储格式"而非"计算格式"：
- 所有运算都转换为 float 进行
- 避免半精度运算的精度累积问题
- 利用现代 CPU 的 float 运算优化

### 延迟内联决策
将转换函数实现在 .cpp 文件中，允许：
- 链接器进行更好的死代码消除
- 编译器根据调用频率决定是否内联
- 保持头文件清爽，减少编译时间

## 性能考量

### 向量化加速
虽然这些函数处理单个值，但底层使用 skvx 向量化库：
- 在支持 F16C 指令集的 x86 CPU 上，转换为单个 VCVTPS2PH/VCVTPH2PS 指令
- 在 ARM NEON 上使用 vcvt 指令
- 回退到软件实现（纯整数位操作）

### 内存节省
使用 half 而非 float 的场景收益：
- **纹理存储**: 对于 RGBA 纹理，每像素从 16 字节降到 8 字节（50%）
- **GPU 传输**: 减少一半的 PCIe 带宽占用
- **缓存友好**: 相同缓存容量可容纳两倍数据

### 转换开销
转换本身有成本，适用场景：
- 数据多次读取但转换一次（纹理采样）
- 内存/带宽是瓶颈而非计算
- GPU 原生支持 FP16 计算（移动 GPU）

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkVx.h | 提供向量化转换实现 |
| src/gpu/ganesh/GrResourceProvider.cpp | 使用 half 创建纹理 |
| src/core/SkRasterPipeline.cpp | 某些管线阶段使用 half |
| include/core/SkColorSpace.h | HDR 颜色空间可能使用 half |
| src/codec/SkPngCodec.cpp | PNG 的高动态范围扩展 |
| src/shaders/*.cpp | 着色器参数打包 |
