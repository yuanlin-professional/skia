# ICU4X Placeholder

> 源文件: bazel/external/icu4x/src/lib.rs

## 概述

`lib.rs` 是 ICU4X 的占位符库文件,用于生成 `Cargo.lock` 文件。ICU4X 是 Unicode Consortium 的国际化组件库的 Rust 实现,提供 Unicode 和全球化支持。该文件包含最小化的代码:一个注释说明其占位符用途,一个版权声明,文档注释解释工作区制约,以及一个 `extern crate` 声明来确保符号链接。

## 架构位置

该文件位于 Skia 项目的外部依赖管理结构中:

```
skia/
  └── bazel/
      └── external/
          └── icu4x/
              └── src/
                  └── lib.rs (本文件)
```

**在构建系统中的位置**:
- **层级**: 外部 Rust 依赖集成层
- **目的**: 支持 ICU4X 的 C API 静态库或动态库编译
- **关联**: 与 `icu_capi_staticlib` 和 `icu_capi_cdylib` crate 配合使用
- **依赖**: 链接 `icu_capi` crate 以包含必要的符号

## 主要类与结构体

该文件不定义任何新的结构体或类型,只包含:

### 1. extern crate 声明

```rust
extern crate icu_capi;
```

**功能**: 声明对 `icu_capi` crate 的外部依赖,确保其符号被链接到最终的库中。

**必要性**: 即使不直接使用 `icu_capi` 的任何项目,这个声明也会使链接器包含该 crate 的所有符号,这对于生成 C API 库至关重要。

## 公共 API 函数

该文件不导出任何公共函数或类型,它只是一个链接点。

## 内部实现细节

### 工作区制约问题

根据文档注释,该文件存在是为了解决 Cargo 的一个限制:

```rust
//! This exists as a separate crate to work around
//! cargo being [unable to conditionally compile crate-types]
```

**问题背景**:
- Cargo 无法根据条件编译不同的 `crate-type`
- 这导致某些目标平台(如 Emscripten)链接失败
- 失败原因是未定义的符号(如 `log_js`),即使该 crate 类型并非所需

**解决方案**:
创建独立的 crate(`icu_capi_staticlib` 和 `icu_capi_cdylib`)作为构建端点:
- `icu_capi_staticlib`: 生成静态库(`.a` 文件)
- `icu_capi_cdylib`: 生成动态库(`.so`/`.dll`/`.dylib` 文件)
- 本文件: 作为其中一个端点的实现

### 符号链接的必要性

```rust
// Necessary for symbols to be linked in
extern crate icu_capi;
```

没有这个声明,编译器可能优化掉未使用的 `icu_capi` crate,导致 C API 符号缺失。通过显式声明,确保所有符号都被包含在最终的库文件中。

### Cargo.lock 生成

与 Vello 占位符类似,该文件使得 Cargo 能够:
1. 识别这是一个有效的 Rust crate
2. 解析依赖关系
3. 生成 `Cargo.lock` 文件锁定版本

## 依赖关系

**直接依赖**:
- `icu_capi`: ICU4X 的 C API 绑定 crate

**传递依赖**:
- `icu_capi` 依赖的所有 ICU4X 核心组件
- Unicode 数据表
- 其他 Rust 标准库 crate

**相关 crate**:
- `icu_capi_staticlib`: 静态库端点
- `icu_capi_cdylib`: 动态库端点

**依赖图**:
```
本文件 (icu4x placeholder)
    └── icu_capi (C API)
        └── icu (核心 Unicode 功能)
            └── Unicode 数据
```

## 设计模式与设计决策

### 1. 工作区模式 (Workaround Pattern)

该文件是针对 Cargo 工具链限制的工作区方案。

**背景问题**:
- Cargo issue #4881: 无法根据条件编译不同的 crate 类型
- Emscripten 等目标需要特定的库类型
- 单一 crate 无法满足多种库类型需求

**解决方案**:
- 创建多个独立的 crate 作为构建端点
- 每个端点对应一种库类型(staticlib/cdylib)
- 共享核心实现(`icu_capi`)

### 2. 符号保留模式

使用 `extern crate` 强制链接器保留所有符号。

**优势**:
- 确保 C API 的完整性
- 避免链接时符号丢失
- 支持动态链接场景

### 3. 最小化桥接

该文件只包含绝对必要的代码,避免引入额外的复杂性。

**优势**:
- 清晰的意图表达
- 降低维护成本
- 减少潜在的构建问题

## 性能考量

该文件对运行时性能没有影响,它只影响编译和链接过程:

### 编译时

- **编译时间**: 该文件编译非常快(几乎瞬间)
- **依赖编译**: `icu_capi` 和其依赖需要较长编译时间
- **链接时间**: 静态链接所有符号会增加链接时间

### 库大小

- **静态库**: 包含所有 ICU4X 符号,可能数 MB
- **动态库**: 类似大小,但运行时加载
- **优化**: 可通过 `cargo` 的 `opt-level` 和 `lto` 配置优化

### 使用场景权衡

**staticlib**:
- 优点: 无需运行时依赖,分发简单
- 缺点: 增加可执行文件大小,无法共享代码

**cdylib**:
- 优点: 多个程序可共享,减少总内存占用
- 缺点: 需要管理动态库版本,分发复杂

## 相关文件

**同包文件**:
- `Cargo.toml`: 定义 crate 元数据和依赖
- `BUILD.bazel`: Bazel 构建规则

**ICU4X 上游仓库**:
- GitHub: `unicode-org/icu4x`
- 许可证: Apache 2.0 或 MIT(根据文件头注释)
- 许可证文件: `LICENSE` (在 ICU4X 源码树顶层)

**相关 Skia 集成**:
- Skia 使用 ICU4X 进行国际化文本处理
- 文本布局和渲染(双向文本、复杂脚本等)
- Unicode 规范化和变换

**Bazel 构建示例**:
```python
# BUILD.bazel
load("@rules_rust//rust:defs.bzl", "rust_library")

rust_library(
    name = "icu4x",
    srcs = ["src/lib.rs"],
    edition = "2021",
    deps = [
        "@crates//:icu_capi",
    ],
    crate_type = "staticlib",  # 或 "cdylib"
)
```

**使用示例**:
```c
// C 代码使用 ICU4X C API
#include "icu_capi.h"

int main() {
    // 使用 ICU4X 进行 Unicode 操作
    ICU4XLocale* locale = icu4x_locale_from_string("zh-CN", 5);
    // ... 其他 ICU4X API 调用
    return 0;
}
```

该占位符文件虽然代码量极少,但在 ICU4X 的 C API 集成和 Bazel 构建系统中起着关键的桥接作用,确保了 Rust 实现的国际化库能够被 C/C++ 代码(如 Skia)正确使用。
