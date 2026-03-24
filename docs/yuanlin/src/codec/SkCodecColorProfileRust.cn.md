# SkCodecColorProfileRust

> 源文件: src/codec/SkCodecColorProfileRust.h, src/codec/SkCodecColorProfileRust.cpp

## 概述

`SkCodecColorProfileRust` 提供基于 Rust 实现的 ICC 颜色配置文件解析功能。该模块通过 FFI (Foreign Function Interface) 调用 Rust 编写的 `moxcms` 库来解析 ICC 配置文件，是 Skia 探索使用 Rust 进行安全内存管理和高性能解析的实验性组件。

该功能仅在定义 `SK_CODEC_COLOR_PROFILE_PARSE_WITH_RUST` 宏时可用，主要用于测试目的。生产代码应使用 `MakeICCProfile()` 函数，它会根据编译配置自动选择合适的实现（Rust 或 C++）。

## 架构位置

在 Skia 颜色管理系统中的位置：

```
SkCodec (解码器)
    ↓
ColorProfile (颜色配置文件)
    ↓
MakeICCProfileWithRust (Rust 实现)
    ↓
rust_icc::parse_icc_profile (Rust 库)
```

**职责**:
- 通过 Rust FFI 解析 ICC 配置文件
- 将 Rust 数据结构转换为 skcms_ICCProfile
- 管理跨语言边界的内存生命周期

## 主要 API 函数

### MakeICCProfileWithRust

```cpp
std::unique_ptr<ColorProfile> MakeICCProfileWithRust(sk_sp<const SkData> data)
```

解析流程：

1. **验证输入数据**
```cpp
if (data) { ... }
```

2. **调用 Rust 解析器**
```cpp
rust_icc::IccProfile rust_profile;
if (rust_icc::parse_icc_profile(
        rust::Slice<const uint8_t>(data->bytes(), data->size()), rust_profile)) {
    // 解析成功
}
```

3. **管理 Rust 对象生命周期**
```cpp
auto retained = std::shared_ptr<rust_icc::IccProfile>(
        new rust_icc::IccProfile(std::move(rust_profile)));
```
将 Rust 配置文件移动到堆上并用 `shared_ptr` 管理，确保其包含的 Vec<u8> 数据在需要时一直存活。

4. **转换为 skcms 格式**
```cpp
skcms_ICCProfile profile;
rust_icc::ToSkcmsIccProfile(*retained, &profile);
```

5. **创建 ColorProfile 对象**
```cpp
auto result = std::unique_ptr<ColorProfile>(
        new ColorProfile(profile, std::move(data)));
result->fRetainedData = retained;  // 保留 Rust 数据
return result;
```

## 内部实现细节

### 跨语言内存管理

关键挑战：`skcms_ICCProfile` 包含指向数据的原始指针（如查找表、曲线表），这些数据存储在 Rust 的 `Vec<u8>` 中。

**解决方案**:
1. 将 Rust 配置文件移动到堆上
2. 使用 `shared_ptr` 包装，确保引用计数管理
3. 将 `shared_ptr` 存储在 `ColorProfile::fRetainedData` 中
4. 只要 `ColorProfile` 存活，Rust 数据就不会被释放

### Rust FFI 边界

使用 `cxx` 库进行 C++/Rust 互操作：
- **rust::Slice**: 零拷贝切片视图
- **rust_icc::IccProfile**: Rust 端定义的配置文件结构
- **parse_icc_profile**: Rust 函数，通过 FFI 导出
- **ToSkcmsIccProfile**: 转换函数，将 Rust 结构映射到 C 结构

## 依赖关系

### 直接依赖
- **SkData**: 输入数据容器
- **SkCodecPriv**: 内部工具和类型定义
- **rust/icc/FFI.rs.h**: Rust FFI 绑定头文件
- **skcms**: 颜色管理系统（C 库）

### 被依赖
- **SkCodec**: 通过 `MakeICCProfile()` 间接使用
- **测试代码**: 直接调用以验证 Rust 实现

## 设计模式与设计决策

### 适配器模式

将 Rust ICC 解析器适配为 Skia 的 `ColorProfile` 接口：
- 隐藏 Rust 实现细节
- 提供统一的 C++ API
- 允许在运行时或编译时切换实现

### RAII 与智能指针

使用 `shared_ptr` 管理 Rust 对象：
- 自动释放 Rust 资源
- 支持多个 `ColorProfile` 共享同一 Rust 数据
- 异常安全

### 实验性标记

仅用于测试，生产代码使用抽象接口：
```cpp
// 测试代码
std::unique_ptr<ColorProfile> profile = MakeICCProfileWithRust(data);

// 生产代码
std::unique_ptr<ColorProfile> profile = MakeICCProfile(data);
```

## 性能考量

### 零拷贝数据传递

使用 `rust::Slice` 传递数据：
- 不复制原始输入数据
- 仅传递指针和长度
- Rust 端只读访问

### Rust 性能优势

Rust 实现的潜在优势：
- 内存安全：无缓冲区溢出风险
- 现代编译器优化
- SIMD 友好的内存布局

### 跨语言调用开销

FFI 调用开销：
- 函数调用本身：可忽略（几纳秒）
- 数据转换：取决于配置文件复杂度
- 内存分配：Rust 端分配，C++ 端包装

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/codec/SkCodecPriv.h` | 依赖 | ColorProfile 类型定义 |
| `include/core/SkData.h` | 依赖 | 数据容器 |
| `rust/icc/FFI.rs.h` | 依赖 | Rust FFI 绑定 |
| `modules/skcms/skcms.h` | 依赖 | skcms_ICCProfile 定义 |
| `src/codec/SkCodecColorProfile.cpp` | 相关 | C++ ICC 解析实现 |
