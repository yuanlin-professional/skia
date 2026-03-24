# MutableTextureState

> 源文件
> - include/gpu/MutableTextureState.h
> - src/gpu/MutableTextureState.cpp

## 概述

`MutableTextureState` 是 Skia GPU 模块中的可变纹理状态封装类,用于在 Skia 和客户端之间同步 GPU 纹理/图像的可变状态。由于 Skia 和客户端都可能修改 GPU 纹理及其相关状态,该类提供了一个通用的包装器,避免为每个 API 和状态单独设置 setter。

该类支持多种 GPU 后端(主要是 Vulkan),封装了后端特定的状态信息,如 Vulkan 的 `VkImageLayout` 和 `QueueFamilyIndex`。

## 架构位置

`MutableTextureState` 位于 Skia GPU 跨平台抽象层,为不同 GPU 后端提供统一的纹理状态管理:

```
skia/
  include/gpu/
    MutableTextureState.h          # 公共接口
    vk/VulkanMutableTextureState.h # Vulkan 特定状态
  src/gpu/
    MutableTextureState.cpp        # 实现
    MutableTextureStatePriv.h      # 内部辅助类
```

该类被 `GrBackendTexture`、`GrBackendRenderTarget` 等后端表面对象使用,用于跟踪和同步纹理状态。

## 主要类与结构体

### MutableTextureState

引用计数的纹理状态容器类。

**继承关系:**
- 基类: `SkRefCnt`
- 派生类: 无(使用组合模式封装后端特定数据)

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fStateData` | `AnyStateData` | 后端特定状态数据(使用 `SkAnySubclass`) |
| `fBackend` | `BackendApi` | GPU 后端类型 |
| `fIsValid` | `bool` | 状态是否已初始化 |

**类型别名:**
```cpp
using AnyStateData = SkAnySubclass<MutableTextureStateData, kMaxSubclassSize>;
```

### MutableTextureStateData

抽象基类,由后端特定实现继承。

**方法:**
- `copyTo()` - 复制状态到目标对象
- 虚析构函数

## 公共 API 函数

### 构造与析构

```cpp
MutableTextureState();
```
**功能:** 创建未初始化的状态对象
**后置条件:** `isValid()` 返回 `false`

```cpp
MutableTextureState(const MutableTextureState& that);
```
**功能:** 拷贝构造函数
**实现:** 调用 `set()` 方法

```cpp
~MutableTextureState() override;
```
**功能:** 析构函数
**特点:** 默认实现

### 操作符重载

```cpp
MutableTextureState& operator=(const MutableTextureState& that);
```
**功能:** 赋值操作符
**实现:** 调用 `set()` 方法,避免自赋值

### 状态管理

```cpp
void set(const MutableTextureState& that);
```
**功能:** 从另一个状态对象复制数据
**参数:** `that` - 源状态对象
**前置条件:** 如果当前对象已有效,后端类型必须匹配
**实现:** 根据后端类型调用特定的 `copyTo` 方法

### 查询方法

```cpp
BackendApi backend() const;
```
**功能:** 获取 GPU 后端类型
**返回:** `BackendApi` 枚举值

```cpp
bool isValid() const;
```
**功能:** 检查状态是否已初始化
**返回:** `true` 表示状态有效

## 内部实现细节

### 模板构造函数

```cpp
template <typename StateData>
MutableTextureState(BackendApi api, const StateData& data);
```
**特点:**
- 私有构造函数,仅供友元类调用
- 使用 `SkAnySubclass` 的 `emplace` 方法就地构造后端数据
- 支持编译期大小检查

### `SkAnySubclass` 存储机制

`SkAnySubclass` 是 Skia 的类型擦除容器:
- 固定大小的内联存储(`kMaxSubclassSize = 16 字节`)
- 避免堆分配,提高性能
- 编译期检查子类大小是否超出限制

### 后端状态复制流程

在 `set()` 方法中,根据 `fBackend` 进行分支:

```cpp
switch (fBackend) {
    case BackendApi::kVulkan:
        that.fStateData->copyTo(fStateData);
        break;
    default:
        SK_ABORT("Unknown BackendApi");
}
```

当前实现仅支持 Vulkan 后端,其他后端触发断言。

### 友元类访问

- `MutableTextureStateData` - 后端数据基类
- `MutableTextureStatePriv` - 内部辅助类,提供特定后端的工厂方法

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkTypes.h` | 基础类型和宏 |
| `include/private/base/SkAnySubclass.h` | 类型擦除容器 |
| `include/gpu/GpuTypes.h` | GPU 类型定义 |
| `src/gpu/MutableTextureStatePriv.h` | 内部辅助类 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrBackendTexture` | 后端纹理封装,使用此类跟踪状态 |
| `GrBackendRenderTarget` | 后端渲染目标,使用此类跟踪状态 |
| `GrDirectContext` | 上下文提供状态同步 API |
| Vulkan 后端 | 封装 `VkImageLayout` 等状态 |

## 设计模式与设计决策

### 设计模式

1. **桥接模式 (Bridge Pattern)**
   - `MutableTextureState` 是抽象接口
   - `MutableTextureStateData` 是实现接口
   - 后端特定类(如 Vulkan 状态)是具体实现

2. **类型擦除 (Type Erasure)**
   - 使用 `SkAnySubclass` 存储任意后端数据
   - 避免虚函数表开销
   - 编译期类型安全

3. **引用计数管理**
   - 继承 `SkRefCnt`,支持智能指针 `sk_sp`
   - 自动生命周期管理

### 设计决策

1. **统一接口设计**
   - 避免为每个后端创建独立类
   - 提供通用的 getter/setter,后端逻辑内部处理

2. **内联存储优化**
   - 使用固定大小的 `SkAnySubclass`,避免堆分配
   - 16 字节足够存储当前所有后端状态

3. **延迟初始化**
   - 默认构造函数创建无效对象
   - 实际状态由后端特定工厂方法设置

4. **后端扩展性**
   - 通过 switch 语句支持多后端
   - 新增后端需修改 `set()` 方法

5. **类型安全**
   - 使用模板构造函数,编译期类型检查
   - `SkAnySubclass` 提供运行时大小验证

## 性能考量

1. **内联存储**
   - 16 字节内联存储,避免堆分配
   - 适合小对象,减少内存碎片

2. **拷贝开销**
   - 拷贝构造和赋值需要复制内部数据
   - 使用引用计数共享,避免不必要的复制

3. **虚函数避免**
   - 使用 `SkAnySubclass` 而非虚函数多态
   - 减少虚函数表查找开销

4. **分支预测**
   - `switch` 语句基于 `fBackend`
   - 现代 CPU 分支预测器可优化常见路径

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/MutableTextureState.h` | 公共接口 |
| `src/gpu/MutableTextureState.cpp` | 实现 |
| `src/gpu/MutableTextureStatePriv.h` | 内部辅助类 |
| `include/gpu/vk/VulkanMutableTextureState.h` | Vulkan 特定状态 |
| `include/gpu/ganesh/GrBackendSurface.h` | 使用状态的后端表面类 |
| `include/gpu/ganesh/GrDirectContext.h` | 提供状态同步 API |
