# BackendTexture

> 源文件
> - include/gpu/graphite/BackendTexture.h
> - src/gpu/graphite/BackendTexture.cpp

## 概述

`BackendTexture` 是 Skia Graphite 渲染系统中对后端 GPU 纹理的跨平台抽象封装。它提供统一的接口来表示不同图形 API（Vulkan、Metal、Dawn）创建的原生纹理对象，同时隐藏底层实现细节。

该类是 Graphite 与底层图形 API 交互的关键桥梁，用于：
- 包装现有的后端纹理（外部纹理导入）
- 表示通过 Recorder 创建的纹理
- 在 Skia 和外部渲染系统间共享纹理资源
- 提供纹理信息查询接口

使用类型擦除技术（`SkAnySubclass`）实现，避免暴露后端特定的类型细节。

## 架构位置

`BackendTexture` 位于 Graphite 的资源抽象层：

- **上层**：被 Image、Surface、Recorder 使用，表示底层纹理资源
- **同层**：与 `BackendSemaphore`、`TextureInfo` 等其他后端对象抽象并列
- **下层**：封装后端特定的纹理句柄（VkImage、MTLTexture 等）
- **所属模块**：`gpu/graphite` - 跨平台资源管理

这是一个值类型对象，支持复制、赋值和比较操作。

## 主要类与结构体

### BackendTexture 类

**继承关系**：
- 无继承，独立实现
- 可复制、可移动、可比较

**关键成员变量**：
| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fDimensions` | `SkISize` | 纹理的宽度和高度 |
| `fInfo` | `TextureInfo` | 纹理格式、用途、mipmap 等信息 |
| `fTextureData` | `AnyBackendTextureData` | 类型擦除的后端纹理数据容器 |

**类型定义**：
```cpp
inline constexpr static size_t kMaxSubclassSize = 72;
using AnyBackendTextureData = SkAnySubclass<BackendTextureData, kMaxSubclassSize>;
```

### BackendTextureData 抽象基类

后端特定纹理数据的基类，提供虚析构函数、`copyTo` 和 `equal` 方法。

**子类实现**：
- `VkBackendTextureData`：封装 VkImage 和相关信息
- `MtlBackendTextureData`：封装 MTLTexture 对象
- `DawnBackendTextureData`：封装 Dawn 纹理对象

## 公共 API 函数

### 构造与析构

```cpp
BackendTexture()
```
默认构造函数，创建无效的纹理对象。

```cpp
BackendTexture(const BackendTexture&)
```
拷贝构造函数，执行深拷贝。

```cpp
~BackendTexture()
```
析构函数，释放内部数据。

### 赋值运算符

```cpp
BackendTexture& operator=(const BackendTexture& that)
```

**实现逻辑**：
1. 检查源对象是否有效，无效则重置当前对象
2. 断言后端类型一致（不允许跨后端赋值）
3. 验证后端是否被支持
4. 复制尺寸、纹理信息和后端数据

### 比较运算符

```cpp
bool operator==(const BackendTexture& that) const
```

**比较逻辑**：
1. 检查双方是否都有效
2. 比较尺寸和 TextureInfo
3. 调用后端数据的 `equal` 方法进行深度比较

```cpp
bool operator!=(const BackendTexture& that) const
```
不等于运算符，等价于 `!(*this == that)`。

### 查询函数

```cpp
bool isValid() const
```
返回纹理是否有效（基于 `fInfo.isValid()`）。

```cpp
BackendApi backend() const
```
返回纹理所属的后端 API 类型。

```cpp
SkISize dimensions() const
```
返回纹理的尺寸（宽度和高度）。

```cpp
const TextureInfo& info() const
```
返回纹理的详细信息（格式、mipmap、样本数等）。

## 内部实现细节

### 类型擦除实现

使用 `SkAnySubclass` 模板存储后端数据：
- 栈上分配最多 72 字节的内联存储
- 避免虚函数表开销
- 支持不同大小的后端数据类型

**构造模板**：
```cpp
template <typename SomeBackendTextureData>
BackendTexture(SkISize dimensions, TextureInfo info, const SomeBackendTextureData& textureData)
        : fDimensions(dimensions), fInfo(info) {
    fTextureData.emplace<SomeBackendTextureData>(textureData);
}
```

### 后端支持验证

赋值运算符中检查后端类型：
```cpp
static inline void assert_is_supported_backend(const BackendApi& backend) {
    SkASSERT(backend == BackendApi::kDawn ||
             backend == BackendApi::kMetal ||
             backend == BackendApi::kVulkan);
}
```

当前支持的后端：
- **Vulkan**：封装 VkImage 和 VkImageLayout
- **Metal**：封装 MTLTexture 对象引用
- **Dawn**：封装 WGPUTexture 句柄

### 复制与比较语义

#### 深拷贝实现
```cpp
fTextureData.reset();
that.fTextureData->copyTo(fTextureData);
```
确保每个 `BackendTexture` 拥有独立的后端数据副本。

#### 相等性比较
```cpp
return fTextureData->equal(that.fTextureData.get());
```
委托给后端特定实现进行深度比较：
- Vulkan：比较 VkImage 句柄和布局
- Metal：比较 MTLTexture 指针
- Dawn：比较 WGPUTexture 句柄

### 有效性判断

纹理有效性取决于 `TextureInfo` 的有效性：
- `TextureInfo::isValid()` 检查格式和配置是否合法
- 默认构造的 `BackendTexture` 无效
- 赋值无效对象会重置当前对象为无效

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `TextureInfo` | 描述纹理格式和属性 |
| `BackendApi` | 枚举后端类型 |
| `SkISize` | 表示纹理尺寸 |
| `SkAnySubclass` | 类型擦除容器 |
| `BackendTexturePriv` | 内部访问接口 |

### 被依赖的模块

- **Recorder**：通过 `createBackendTexture` 创建纹理
- **Context**：删除 BackendTexture
- **Image/Surface**：包装 BackendTexture 用于渲染
- **TextureProxy**：内部使用 BackendTexture 表示 GPU 纹理

## 设计模式与设计决策

### 值语义设计

`BackendTexture` 是值类型：
- 支持拷贝和赋值（深拷贝）
- 栈分配，无需显式内存管理
- 生命周期由持有者控制

这与纹理句柄的轻量级特性一致，但需注意深拷贝的开销。

### 类型擦除而非继承

优势：
- 避免虚函数调用开销
- 保持对象大小可预测（约 88 字节）
- 编译期类型安全
- 无需堆内存分配

劣势：
- 复制操作涉及后端数据的完整拷贝
- 不支持运行时多态扩展

### 不可变尺寸和格式

一旦创建，`fDimensions` 和 `fInfo` 不可修改：
- 简化资源管理
- 避免纹理重新分配
- 提高缓存效率

### 显式后端类型检查

赋值和比较操作都检查后端一致性：
- 防止跨后端操作错误
- 在开发期通过断言捕获问题
- 保证类型安全

## 性能考量

### 内存布局

- 固定大小（约 88 字节：8 + 8 + 72）
- 内联存储避免堆分配
- 缓存友好的紧凑布局

### 复制开销

拷贝构造和赋值涉及：
- 基本类型复制（尺寸、TextureInfo）
- 后端数据深拷贝（可能包含对象引用计数增加）

建议：
- 按 const 引用传递以避免不必要的复制
- 使用 std::move 传递所有权
- 复用 BackendTexture 对象

### 比较开销

相等性比较涉及：
- 尺寸和 TextureInfo 的逐字段比较
- 后端数据的深度比较（可能涉及指针解引用）

建议：先比较尺寸和格式，再调用 `operator==`。

### 后端特定优化

- **Vulkan**：句柄比较是廉价的
- **Metal**：对象引用比较涉及 Objective-C 消息传递
- **Dawn**：句柄比较是廉价的

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/graphite/TextureInfo.h` | 纹理属性描述 |
| `include/gpu/GpuTypes.h` | BackendApi 枚举 |
| `include/core/SkSize.h` | SkISize 定义 |
| `include/private/base/SkAnySubclass.h` | 类型擦除容器 |
| `src/gpu/graphite/BackendTexturePriv.h` | 内部访问接口 |
| `src/gpu/graphite/vk/VkTexture.h` | Vulkan 纹理封装 |
| `src/gpu/graphite/mtl/MtlTexture.h` | Metal 纹理封装 |
| `src/gpu/graphite/dawn/DawnTexture.h` | Dawn 纹理封装 |
| `include/gpu/graphite/Recorder.h` | 创建 BackendTexture 的接口 |
