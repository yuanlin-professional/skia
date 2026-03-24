# DisplayParams 显示参数配置

> 源文件: `tools/window/DisplayParams.h`

## 概述

此头文件定义了 Skia 窗口系统（`skwindow` 命名空间）中的 `DisplayParams` 类和 `DisplayParamsBuilder` 构建器类。`DisplayParams` 封装了创建渲染目标表面时所需的所有显示配置参数，包括颜色类型、颜色空间、MSAA 采样数、表面属性和 GPU 上下文选项等。它被设计为不可变对象，一旦创建后参数不应被修改，所有配置都通过 Builder 模式完成。

## 架构位置

- 所属模块：`tools/window/`（Skia 窗口抽象层）
- 角色：渲染表面创建的参数容器
- 消费者：Skia Viewer、各平台窗口后端（Win、Mac、Linux、Android）
- 命名空间：`skwindow`

## 主要类与结构体

### `DisplayParams`
不可变的显示参数类。

**核心字段：**
| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `fColorType` | `SkColorType` | `kN32_SkColorType` | 像素颜色格式 |
| `fColorSpace` | `sk_sp<SkColorSpace>` | nullptr | 颜色空间（nullptr=sRGB） |
| `fMSAASampleCount` | `int` | 1 | MSAA 抗锯齿采样数 |
| `fGrContextOptions` | `GrContextOptions` | 默认 | Ganesh GPU 上下文选项（仅 SK_GANESH） |
| `fSurfaceProps` | `SkSurfaceProps` | `{0, kRGB_H}` | 表面属性（LCD 方向等） |
| `fDisableVsync` | `bool` | false | 禁用垂直同步 |
| `fDelayDrawableAcquisition` | `bool` | false | 延迟可绘制对象获取 |
| `fCreateProtectedNativeBackend` | `bool` | false | 创建受保护的原生后端 |

**主要方法：**
- 所有 getter 方法（`colorType()`、`colorSpace()` 等）
- `clone()`：虚克隆方法，支持子类复制
- 拷贝构造函数和指针构造函数
- `graphiteTestOptions()`：虚方法，返回 Graphite 测试选项

### `DisplayParamsBuilder`
Builder 模式构建器，唯一允许修改 `DisplayParams` 内部字段的途径。

**核心字段：**
- `fDisplayParams`：被构建的 `unique_ptr<DisplayParams>`

**链式方法：**
| 方法 | 描述 |
|------|------|
| `colorType(type)` | 设置颜色类型 |
| `colorSpace(space)` | 设置颜色空间 |
| `msaaSampleCount(count)` | 设置 MSAA 采样数 |
| `roundUpMSAA()` | 将 MSAA 采样数向上取到 2 的幂 |
| `grContextOptions(options)` | 设置 Ganesh GPU 上下文选项 |
| `surfaceProps(props)` | 设置表面属性 |
| `disableVsync(disable)` | 设置 VSync 禁用 |
| `delayDrawableAcquisition(delay)` | 设置延迟获取 |
| `createProtectedNativeBackend(protect)` | 设置受保护后端 |
| `detach()` | 释放并返回构建完成的 DisplayParams |

## 公共 API 函数

### DisplayParams 访问器
所有 getter 方法均为 `const`，保证不可变性。`graphiteTestOptions()` 为虚方法，允许子类提供 Graphite 特定的测试选项。

### DisplayParamsBuilder 构造
- 默认构造：创建带默认值的 DisplayParams
- 复制构造：从已有 DisplayParams 克隆（通过 `clone()` 支持子类）
- 受保护构造：接受已有的 `unique_ptr<DisplayParams>`，用于子类 Builder 的扩展

## 内部实现细节

### 不可变设计
- `DisplayParams` 的所有字段为 `private`
- 仅 `DisplayParamsBuilder` 被声明为 `friend class`，拥有写入权限
- 公开的接口全部为只读 getter

### 条件编译
- `#if defined(SK_GANESH)` 包裹 Ganesh GPU 相关字段和方法
- 确保在不编译 Ganesh 后端时不引入 GPU 依赖

### MSAA 向上取整
`roundUpMSAA()` 使用 `SkNextPow2` 将采样数向上取到 2 的幂，因为 GPU 硬件通常只支持 2 的幂次采样数。对 0 和 1 特殊处理。

### 默认表面属性
默认使用 `kRGB_H_SkPixelGeometry`（水平 RGB 子像素排列），这是最常见的 LCD 屏幕配置。

## 依赖关系

- `include/core/SkColorSpace.h`：颜色空间
- `include/core/SkImageInfo.h`：颜色类型
- `include/core/SkSurfaceProps.h`：表面属性
- `src/base/SkMathPriv.h`：`SkNextPow2`
- `include/gpu/ganesh/GrContextOptions.h`：GPU 上下文选项（条件编译）
- 前向声明：`skiatest::graphite::TestOptions`

## 设计模式与设计决策

- **Builder 模式**：通过 Builder 实现链式配置，确保对象创建后的不可变性
- **友元限制**：仅 Builder 可修改内部字段，强制通过 Builder 进行配置
- **虚克隆模式**：`clone()` 方法允许子类正确复制，Builder 的复制构造通过 `clone()` 实现
- **条件编译隔离**：GPU 相关功能通过条件编译隔离，保持非 GPU 环境下的编译兼容性
- **不可变对象模式**：创建后参数不可变，避免多线程环境下的数据竞争

## 性能考量

- `DisplayParams` 作为值对象，拷贝开销较小（除 `sk_sp<SkColorSpace>` 需要引用计数操作）
- `unique_ptr` 语义确保 Builder 不会意外共享正在构建的对象
- `clone()` 使用 `make_unique` 而非 `new`，利用编译器优化
- MSAA 采样数的 2 次幂向上取整确保与 GPU 硬件对齐，避免运行时降级

## 相关文件

- `tools/window/WindowContext.h` - 使用 DisplayParams 的窗口上下文
- `tools/viewer/Viewer.cpp` - Skia Viewer 应用（主要消费者）
- `include/gpu/ganesh/GrContextOptions.h` - Ganesh GPU 选项
- `include/core/SkSurfaceProps.h` - 表面属性定义
