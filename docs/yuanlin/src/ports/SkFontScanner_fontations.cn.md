# SkFontScanner_fontations

> 源文件: [src/ports/SkFontScanner_fontations.cpp](../../../../src/ports/SkFontScanner_fontations.cpp)

## 概述

本文件实现了 `SkFontScanner_Fontations` 类，即基于 Google Fontations (Rust) 库的字体扫描器。它负责扫描字体文件以获取字体面数量、命名实例数量、字体元数据（名称、样式、可变轴等），并提供从字体流创建 `SkTypeface` 的能力。所有字体解析工作通过 Rust FFI 桥接调用 Fontations 库完成。

## 架构位置

```
SkFontScanner (纯虚接口)
  ├── SkFontScanner_FreeType (FreeType C 库后端)
  └── SkFontScanner_Fontations (本文件: Fontations Rust 后端)
        ├── fontations_ffi:: (Rust FFI 桥接层)
        └── SkTypeface_Fontations (字体面实现)
```

## 主要类与结构体

### SkFontScanner_Fontations

实现 `SkFontScanner` 接口的所有方法，通过 Fontations FFI 调用 Rust 代码解析字体。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool scanFile(SkStreamAsset*, int* numFaces) const` | 扫描字体文件/集合，返回包含的字体面数量 |
| `bool scanFace(SkStreamAsset*, int faceIndex, int* numInstances) const` | 扫描指定字体面，返回命名实例数量 |
| `bool scanInstance(...)` | 扫描指定实例，获取名称、样式、等宽属性、变轴、变体位置 |
| `sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset>, const SkFontArguments&) const` | 从流创建字体面 |
| `SkTypeface::FactoryId getFactoryId() const` | 返回 Fontations 工厂标识 |

### 工厂函数

| 函数签名 | 功能说明 |
|---------|---------|
| `std::unique_ptr<SkFontScanner> SkFontScanner_Make_Fontations()` | 创建 Fontations 扫描器实例 |

## 内部实现细节

### 辅助函数

#### `make_bridge_font_ref(const SkData*, uint32_t index)`
通过 FFI 调用 Rust 的 `fontations_ffi::make_font_ref()`，创建指向字体数据的桥接引用。`rust::Slice<const uint8_t>` 提供零拷贝的数据访问。

#### `make_data_avoiding_copy(SkStreamAsset*)`
优化数据获取策略，避免不必要的数据拷贝:
1. 优先尝试 `stream->getData()` 获取已有的 `SkData`
2. 其次尝试 `stream->getMemoryBase()` 创建零拷贝引用
3. 最后退化为 `SkData::MakeFromStream()` 完整读取

#### `make_normalized_coords(...)`
将用户指定的变体坐标转换为字体的归一化坐标，通过 `resolve_into_normalized_coords()` FFI 调用实现。

### scanFile - 字体文件扫描

1. 通过 `make_data_avoiding_copy` 获取字体数据
2. 调用 `fontations_ffi::font_or_collection()` 判断是单一字体还是字体集合
3. 单一字体 (`num_fonts == 0`) 返回 1，集合返回实际数量
4. 每次操作后调用 `stream->rewind()` 重置流位置

### scanFace - 字体面扫描

1. 创建指定索引的桥接字体引用
2. 验证引用有效性
3. 调用 `fontations_ffi::num_named_instances()` 获取命名实例数

### scanInstance - 实例扫描（最复杂的方法）

处理流程:
1. **获取字体名称**: 通过 `fontations_ffi::family_name()` 获取
2. **获取字体样式** (分三种情况):
   - `instanceIndex == 0`: 默认实例，使用空坐标获取样式
   - `instanceIndex > num`: 越界，返回 false
   - 其他: 命名实例，提取坐标后获取样式
3. **获取变轴定义**: 通过 `fontations_ffi::num_axes()` 和 `fontations_ffi::populate_axes()` 获取
4. **获取变体位置**: 从命名实例的坐标中提取

命名实例的索引编码方式: `instanceIndex << 16`（高 16 位为实例索引，低 16 位为面索引）。

### MakeFromStream / getFactoryId

简单委托给 `SkTypeface_Fontations` 的对应静态方法:
```cpp
sk_sp<SkTypeface> SkFontScanner_Fontations::MakeFromStream(...) {
    return SkTypeface_Fontations::MakeFromStream(std::move(stream), args);
}

SkTypeface::FactoryId SkFontScanner_Fontations::getFactoryId() const {
    return SkTypeface_Fontations::FactoryId;  // 即 'fnta'
}
```

### SkFontScanner_Make_Fontations

全局工厂函数，返回 `std::make_unique<SkFontScanner_Fontations>()`，供字体管理器在初始化时调用。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/ports/SkFontScanner_Fontations.h` | 公共头文件 |
| `src/ports/SkFontScanner_fontations_priv.h` | 私有声明 |
| `src/ports/SkTypeface_fontations_priv.h` | Fontations 字体面 |
| `src/ports/fontations/src/skpath_bridge.h` | Rust FFI 桥接定义 |
| `src/sfnt/SkOTUtils.h` | OpenType 工具 |
| Fontations (Rust crate) | 通过 CXX FFI 调用 |

## 设计模式与设计决策

1. **零拷贝数据传递**: `make_data_avoiding_copy` 尽可能避免字体数据拷贝，通过 `rust::Slice` 传递引用
2. **Rust-C++ FFI (CXX)**: 使用 CXX 库实现类型安全的 Rust-C++ 互操作
3. **命名实例索引编码**: 使用高 16 位/低 16 位编码方式将面索引和实例索引打包在一个整数中
4. **流重置模式**: 每次 FFI 调用后调用 `stream->rewind()`，确保流可被后续操作重复使用
5. **静态类型转换**: 通过 `static_assert` 验证 C++ 和 Rust 结构体布局匹配，安全使用 `reinterpret_cast`
6. **数据所有权**: `sk_sp<const SkData>` 确保字体数据在 FFI 调用期间保持有效

## 性能考量

- `make_data_avoiding_copy` 的三级回退策略最大限度减少数据拷贝:
  - 第一级: `stream->getData()` 直接共享引用
  - 第二级: `stream->getMemoryBase()` 零拷贝包装
  - 第三级: `SkData::MakeFromStream()` 完整读取（最慢）
- FFI 边界调用有固定开销，但字体扫描通常是低频操作
- `rust::Slice` 和 `rust::Box` 提供零拷贝的所有权传递
- 每个扫描方法独立创建桥接引用，不缓存状态，适合并发场景
- `stream->rewind()` 调用确保流位置一致性，但增加少量 I/O 开销
- `scanInstance` 中对命名实例的坐标提取涉及动态内存分配 (`std::unique_ptr<Coordinate[]>`)

## 使用场景

本扫描器在以下场景中被使用:
- 字体管理器 (如 `SkFontMgr_fontations_empty`) 在枚举和加载字体时使用
- `SkFontScanner_Make_Fontations()` 工厂函数在字体管理器初始化时被调用
- 处理 TTC (TrueType Collection) 字体文件时，先通过 `scanFile` 获取面数量，再逐一扫描

## 错误处理

所有扫描方法在遇到以下情况时返回 `false`:
- 字体数据无法解析 (`font_or_collection` 失败)
- 字体引用无效 (`font_ref_is_valid` 返回 false)
- 命名实例索引超出范围
- 坐标提取的两次调用返回数量不一致

## 相关文件

- `src/ports/SkFontScanner_fontations_priv.h` — 类声明
- `src/ports/SkTypeface_fontations_priv.h` — Fontations 字体面实现
- `src/ports/fontations/src/skpath_bridge.h` — FFI 桥接层定义
- `src/ports/SkFontScanner_FreeType_priv.h` — FreeType 后端对应实现
- `include/core/SkFontScanner.h` — 扫描器接口定义
