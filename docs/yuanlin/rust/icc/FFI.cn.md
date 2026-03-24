# rust_icc FFI

> 源文件: rust/icc/FFI.h, rust/icc/FFI.cpp, rust/icc/FFI.rs

## 概述

`rust_icc` FFI 模块是 Skia 中用于 ICC 色彩配置文件解析的 Rust-C++ 互操作层。该模块通过 CXX bridge 实现了 Rust 侧的 `moxcms` ICC 解析器与 C++ 侧的 `skcms` 色彩管理系统之间的桥接。模块的核心功能是将 ICC 配置文件数据在 Rust 中安全解析后,转换为 skcms 兼容的 C++ 数据结构,用于后续的色彩空间转换和颜色管理操作。

该模块的设计理念是利用 Rust 的内存安全特性来处理潜在不可信的 ICC 数据解析,同时保持与现有 skcms 生态系统的完全兼容性。所有解析工作在 Rust 侧完成,然后通过零拷贝或最小拷贝的方式将数据暴露给 C++ 侧使用。

## 架构位置

```
skia/
├── modules/skcms/          # C++ 色彩管理库
│   └── skcms.h            # skcms 公共 API
├── rust/
│   ├── icc/
│   │   ├── FFI.h          # C++ 头文件,声明转换函数
│   │   ├── FFI.cpp        # C++ 实现,类型转换逻辑
│   │   └── FFI.rs         # Rust 实现,ICC 解析和 CXX 桥接
│   └── common/            # Rust 通用工具
└── tests/
    └── RustIccTest.cpp    # FFI 往返测试
```

该模块位于 Skia 的 Rust 互操作层,是 Rust 色彩管理组件与 C++ 核心图形系统之间的关键接口。它依赖外部 `moxcms` crate 进行实际的 ICC 解析工作。

## 主要类与结构体

### C++ 侧 (FFI.h/FFI.cpp)

**`rust_icc::Matrix3x3`**
- 3×3 浮点矩阵,用于色彩空间变换
- 与 `skcms_Matrix3x3` 内存布局完全兼容
- 成员:`float vals[3][3]`

**`rust_icc::TransferFunction`**
- 传递函数参数,定义伽马曲线
- 字段顺序: g, a, b, c, d, e, f
- 表示公式: `y = (ax + b)^g + c` (当 x ≥ d) 或 `y = ex + f` (当 x < d)

**`rust_icc::Curve`**
- 查找表(LUT)变换曲线,支持参数化或基于表的表示
- `table_entries`: 0 表示参数化,>0 表示表格
- `table_data`: u16 值的大端字节序存储

**`rust_icc::A2B`**
- 设备到 PCS(Profile Connection Space)的变换
- 包含输入曲线、CLUT 网格、矩阵、输出曲线
- 支持 1-4 输入通道和 1-4 输出通道

**`rust_icc::B2A`**
- PCS 到设备的变换,A2B 的逆向
- 结构与 A2B 相似但变换方向相反

**`rust_icc::IccProfile`**
- 完整的 ICC 配置文件解析结果
- 包含色彩空间、toXYZD50 矩阵、TRC 曲线、CICP 元数据、A2B/B2A 变换

### Rust 侧 (FFI.rs)

**`ffi::skcms_Signature` (enum)**
- 色彩空间类型枚举,与 skcms 值匹配
- 支持 RGB, Gray, CMYK, Lab, XYZ 等多种色彩空间
- 使用 `#[repr(u32)]` 确保 ABI 兼容

**`LutTagType` (enum)**
- 标识 A2B 或 B2A 标签类型
- 影响 PCS XYZ 转换时应用的编码因子

## 公共 API 函数

### C++ API

**`void ToSkcmsMatrix3x3(const Matrix3x3& rust_matrix, skcms_Matrix3x3* out_skcms)`**
- 转换 Rust Matrix3x3 到 skcms_Matrix3x3
- 使用 `memcpy` 进行零开销转换
- 包含编译期静态断言验证布局兼容性

**`void ToSkcmsTransferFunction(const TransferFunction& rust_tf, skcms_TransferFunction* out_skcms)`**
- 转换 Rust TransferFunction 到 skcms_TransferFunction
- 验证字段偏移量以确保正确的内存布局

**`bool ToSkcmsIccProfile(const IccProfile& rust_profile, skcms_ICCProfile* out_skcms)`**
- 核心转换函数,将 Rust 解析的 ICC 配置文件转换为 skcms 结构
- 填充所有 skcms 字段:色彩空间元数据、toXYZD50 矩阵、传递曲线、CICP、A2B/B2A
- **重要生命周期约束**: `out_skcms` 的生命周期不得超过 `rust_profile`,因为 LUT 数据指针引用 Rust 所有的内存
- 返回 `true` 表示成功,`false` 表示缺少必要数据

### Rust API

**`pub fn parse_icc_profile(data: &[u8], out: &mut ffi::IccProfile) -> bool`**
- 解析 ICC 配置文件字节流
- 使用 `moxcms::ColorProfile::new_from_slice()` 进行解析
- 验证签名、大小和结构有效性
- 填充 `IccProfile` 结构的所有字段
- 返回 `true` 表示成功解析,`false` 表示失败

## 内部实现细节

### 类型转换和内存安全

C++ 侧使用大量静态断言确保类型安全:
```cpp
static_assert(sizeof(Matrix3x3) == sizeof(skcms_Matrix3x3), "...");
static_assert(alignof(Matrix3x3) == alignof(skcms_Matrix3x3), "...");
static_assert(std::is_standard_layout_v<Matrix3x3>, "...");
static_assert(std::is_trivially_copyable_v<Matrix3x3>, "...");
```

这些断言确保 Rust 和 C++ 类型可以安全地通过 `memcpy` 转换,避免字段对齐或大小不匹配导致的未定义行为。

### ICC 解析流程

1. **验证阶段**: Rust 侧使用 moxcms 验证 ICC 签名、长度和基本结构
2. **色彩空间映射**: 将 moxcms DataColorSpace 枚举转换为 skcms_Signature
3. **矩阵提取**: 从 colorant tags (rXYZ, gXYZ, bXYZ) 提取 toXYZD50 矩阵
4. **TRC 转换**: 支持参数化曲线和查找表两种形式
5. **LUT 处理**: 转换 A2B/B2A 多维查找表,包括输入/输出曲线和 CLUT 网格

### 编码因子处理

对于 PCS XYZ 色彩空间,skcms 在 A2B 和 B2A 标签中应用不同的编码因子:
- A2B: `65535.0 / 32768.0` (从设备值缩放到 PCS XYZ)
- B2A: `32768.0 / 65535.0` (从 PCS XYZ 缩放到设备值)

`apply_encoding_factor()` 函数根据 `LutTagType` 对矩阵和偏置应用相应的缩放。

### 字节序转换

ICC 规范使用大端字节序存储 16 位数据。`u16_vec_to_bytes()` 函数将 u16 向量转换为大端字节流,确保 skcms 可以正确解释查找表数据:
```rust
fn u16_vec_to_bytes(values: &[u16]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(values.len() * 2);
    for value in values {
        bytes.extend(value.to_be_bytes());
    }
    bytes
}
```

### 曲线转换策略

对于传递曲线,模块采用不同策略:
- **单条目 curv 标签**: 表示伽马值(8.8 定点),转换为参数化曲线
- **多条目 curv 标签**: 直接传递大端 u16 表,由 skcms 精确插值
- **parametric 曲线**: 转换 moxcms ParametricCurve 为 skcms TransferFunction

这种设计避免了参数化近似导致的 ±1 ULP 误差。

### A2B 到 B2A 转换

`a2b_to_b2a()` 函数通过交换输入/输出曲线实现 A2B 到 B2A 的转换:
```rust
fn a2b_to_b2a(a2b: ffi::A2B) -> ffi::B2A {
    ffi::B2A {
        input_curves: a2b.output_curves,
        input_channels: a2b.output_channels,
        // ... 矩阵和网格保持不变 ...
        output_curves: a2b.input_curves,
        output_channels: a2b.input_channels,
    }
}
```

### GRAY 配置文件特殊处理

对于没有 colorant 矩阵(rXYZ/gXYZ/bXYZ 标签)的 GRAY XYZ 配置文件,模块从 ICC 头部的白点(必须是 D50)合成对角 toXYZD50 矩阵:
```rust
if !out.has_to_xyzd50 && profile.color_space == Gray && profile.pcs == Xyz {
    let wp = &profile.white_point;
    out.to_xyzd50 = ffi::Matrix3x3 {
        vals: [[wp.x, 0.0, 0.0], [0.0, wp.y, 0.0], [0.0, 0.0, wp.z]],
    };
    out.has_to_xyzd50 = true;
}
```

## 依赖关系

### 外部依赖
- **moxcms**: Rust ICC 解析库(Chromium 的 moxcms crate)
- **cxx**: Rust-C++ 互操作框架
- **modules/skcms**: Skia 的 C 色彩管理系统

### 内部依赖
- `rust/icc/FFI.rs.h`: CXX 桥接自动生成的头文件

### 依赖方向
```
C++ 调用者 → FFI.h/FFI.cpp → FFI.rs → moxcms crate
              ↓
         skcms.h (类型定义)
```

## 设计模式与设计决策

### 1. CXX 桥接模式
使用 `#[cxx::bridge]` 宏生成类型安全的 Rust-C++ 互操作代码,避免手动编写 extern "C" 绑定。

### 2. 零拷贝借用
LUT 表数据通过指针从 Rust 借用到 C++,避免大量内存拷贝。调用者必须确保生命周期正确。

### 3. 类型安全的枚举映射
使用详尽的 match 表达式(无 catch-all 模式)映射 moxcms 枚举到 skcms 枚举,确保新增枚举值时编译失败提示更新。

### 4. 静态断言防御
大量使用编译期静态断言验证类型布局兼容性,将潜在运行时错误提前到编译期。

### 5. 可选字段模式
使用 `has_*` 布尔标志表示可选字段是否有效,匹配 skcms 的 API 风格。

### 6. 双向转换支持
同时支持 A2B 和 B2A 转换,通过 `LutTagType` 枚举区分处理逻辑。

### 7. 错误处理策略
解析失败返回 `false` 而非抛出异常,符合 C++ 和 Rust 的错误处理惯例。

## 性能考量

### 1. 内存布局优化
- 通过 `#[repr(C)]` 确保 Rust 结构体使用 C 内存布局
- 使用 `memcpy` 进行平凡可拷贝类型的高效转换
- 避免不必要的内存分配和拷贝

### 2. 大端字节序转换
虽然需要转换字节序,但 `u16_vec_to_bytes()` 一次性完成转换并分配内存,避免多次分配。

### 3. 延迟计算
只在需要时转换 A2B 到 B2A,避免预先计算所有可能的变换。

### 4. 零拷贝数据共享
LUT 表数据通过 `.data()` 指针共享,C++ 侧只持有指针而不复制数据。这要求调用者谨慎管理生命周期,但换来了显著的性能提升。

### 5. 编译期优化
静态断言和 inline 函数允许编译器进行更激进的优化,如内联和常量折叠。

### 6. 向量化潜力
连续的内存布局(如 `vals[3][3]`)有利于 SIMD 优化,虽然当前代码未显式向量化。

## 相关文件

### 核心实现
- `rust/icc/FFI.h`: C++ 接口头文件
- `rust/icc/FFI.cpp`: C++ 转换函数实现
- `rust/icc/FFI.rs`: Rust 解析器和 CXX 桥接
- `rust/icc/FFI.rs.h`: CXX 自动生成的头文件

### 依赖和测试
- `modules/skcms/skcms.h`: skcms 公共 API 和类型定义
- `tests/RustIccTest.cpp`: FFI 往返测试
- `rust/common/`: Rust 通用工具(如 SpanUtils)

### 相关模块
- `rust/png/FFI.rs`: PNG 解码器的类似 FFI 实现
- `src/core/SkColorSpace.cpp`: 使用 ICC 配置文件的 Skia 色彩空间实现
- `modules/skcms/skcms.cc`: skcms 内部实现

### 构建文件
- `rust/icc/BUILD.bazel` 或 `rust/icc/BUILD.gn`: 构建配置
- `Cargo.toml`: Rust 依赖配置(moxcms, cxx)
