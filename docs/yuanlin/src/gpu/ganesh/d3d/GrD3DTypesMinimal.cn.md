# GrD3DTypesMinimal

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DTypesMinimal.cpp`

## 概述

`GrD3DTypesMinimal` 是实现 `GrD3DBackendSurfaceInfo` 类的源文件,该类是 Direct3D 12 后端表面信息的最小化封装。`GrD3DBackendSurfaceInfo` 作为跨 API 边界传递 D3D12 表面信息的容器,封装了纹理资源信息和资源状态,提供了完整的拷贝语义和移动语义支持。

该类位于 Skia 的公共 API 边界,允许外部代码与 Skia 的 D3D12 后端交互,例如导入外部创建的 D3D12 纹理或导出 Skia 创建的纹理供外部使用。它通过智能指针管理资源状态,支持多个对象共享同一资源的状态跟踪。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── D3D12 公共 API 层
    ├── GrBackendSurface (跨后端抽象)
    └── GrD3DBackendSurfaceInfo (D3D12 特定实现)
        ├── GrD3DTextureResourceInfo (纹理信息)
        └── GrD3DResourceState (状态跟踪)
```

该类是 Ganesh D3D12 后端与外部世界的接口,位于公共 API 层。

## 主要类与结构体

### GrD3DBackendSurfaceInfo

该类封装了 D3D12 表面的完整信息。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTextureResourceInfo` | `std::unique_ptr<GrD3DTextureResourceInfo>` | 纹理资源信息的独占指针 |
| `fResourceState` | `sk_sp<GrD3DResourceState>` | 资源状态跟踪的共享指针 |

**设计特点:** 使用 `unique_ptr` 管理纹理信息(深拷贝),使用 `sk_sp` 共享资源状态(浅拷贝)。

## 公共 API 函数

### 构造函数

```cpp
GrD3DBackendSurfaceInfo(const GrD3DTextureResourceInfo& info,
                        sk_sp<GrD3DResourceState> state);
```

从纹理资源信息和状态对象构造表面信息。纹理信息被深拷贝,状态对象被共享。

### 拷贝语义

```cpp
GrD3DBackendSurfaceInfo(const GrD3DBackendSurfaceInfo& that);
GrD3DBackendSurfaceInfo& operator=(const GrD3DBackendSurfaceInfo& that);
```

**拷贝行为:**
- 深拷贝纹理资源信息(`new GrD3DTextureResourceInfo(*)`)
- 浅拷贝资源状态对象(共享 `sk_sp`)

**自赋值保护:** 赋值运算符检查 `this != &that` 避免自赋值问题。

### 移动语义

```cpp
GrD3DBackendSurfaceInfo(GrD3DBackendSurfaceInfo&&) = default;
GrD3DBackendSurfaceInfo& operator=(GrD3DBackendSurfaceInfo&&) = default;
```

使用编译器生成的默认移动语义,效率高且正确。

### 资源状态管理

```cpp
void setResourceState(GrD3DResourceStateEnum resourceState);
```
设置资源状态。更新共享的状态对象,影响所有引用该状态的对象。

```cpp
sk_sp<GrD3DResourceState> getResourceState() const;
```
获取资源状态跟踪对象的智能指针。

### 快照纹理资源信息

```cpp
GrD3DTextureResourceInfo snapTextureResourceInfo() const;
```

创建纹理资源信息的快照,包含当前的资源状态。返回值包含状态的即时副本。

### 保护内存查询

```cpp
bool isProtected() const;
```

检查纹理是否使用受保护的 GPU 内存(用于 DRM 内容保护)。

### 相等性比较

```cpp
bool operator==(const GrD3DBackendSurfaceInfo& that) const;
```

仅在测试环境中可用(`GPU_TEST_UTILS`)。比较两个表面信息是否相等,忽略资源状态的具体值,但要求共享同一状态对象。

## 内部实现细节

### 深浅拷贝混合

拷贝构造和赋值的实现策略:

**纹理资源信息(深拷贝):**
```cpp
fTextureResourceInfo.reset(new GrD3DTextureResourceInfo(*that.fTextureResourceInfo));
```
每个对象拥有独立的纹理信息副本。

**资源状态(浅拷贝):**
```cpp
fResourceState = that.fResourceState;
```
多个表面信息对象共享同一资源状态跟踪器。

**原因:** 资源状态需要在多个引用之间同步更新,而纹理信息是静态的元数据。

### 状态快照机制

`snapTextureResourceInfo` 创建包含当前状态的副本:
```cpp
return GrD3DTextureResourceInfo(
    *fTextureResourceInfo,
    static_cast<D3D12_RESOURCE_STATES>(fResourceState->getResourceState()));
```

这允许捕获特定时刻的完整资源配置。

### 资源状态枚举转换

`setResourceState` 接受 `GrD3DResourceStateEnum`:
- 这是一个最小化的枚举类型(不依赖完整 D3D12 头文件)
- 转换为 `D3D12_RESOURCE_STATES` 后设置到状态对象
- 减少公共头文件的依赖

### 测试专用相等性比较

相等性运算符的实现:
1. 复制两个对象的纹理信息
2. 将状态字段归一化为 `COMMON` (忽略状态差异)
3. 比较纹理信息和状态对象指针

**语义:** 检查是否表示同一资源的同一视图,而非状态是否相同。

### 移动优化

移动构造和移动赋值使用编译器默认实现:
- `unique_ptr` 的移动转移所有权
- `sk_sp` 的移动避免引用计数操作
- 零拷贝,仅指针交换

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrD3DTypesMinimal.h` | 声明 `GrD3DBackendSurfaceInfo` |
| `GrD3DTypes` | 完整的 D3D12 类型定义 |
| `GrD3DResourceState` | 资源状态跟踪 |
| `GrD3DTypesPriv` | 私有类型定义 |
| `<memory>` | 智能指针类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrBackendSurface` | 封装 D3D12 特定信息 |
| 外部应用代码 | 导入/导出 D3D12 表面 |
| `GrD3DGpu` | 处理后端表面信息 |

## 设计模式与设计决策

### 桥接模式

`GrD3DBackendSurfaceInfo` 作为桥接:
- 连接 Skia 内部实现和外部 API
- 隐藏实现细节(通过 `unique_ptr` 的 PIMPL)
- 提供稳定的 ABI 边界

### 最小化公共依赖

通过 `GrD3DTypesMinimal` 和 `GrD3DResourceStateEnum`:
- 减少公共头文件对 D3D12 SDK 的依赖
- 允许在不包含 `<d3d12.h>` 的代码中使用
- 改善编译时间和模块化

### 智能指针策略

不同成员使用不同的智能指针:
- `unique_ptr` 用于独占的纹理信息
- `sk_sp` 用于共享的资源状态
- 明确了所有权和共享语义

### 值语义 vs 引用语义

类提供完整的值语义:
- 可拷贝、可移动、可赋值
- 允许在容器中存储
- 便于在不同作用域传递

### 懒加载状态快照

`snapTextureResourceInfo` 按需创建快照:
- 不在对象中预存快照
- 减少内存占用
- 仅在需要时付出拷贝成本

### 条件编译的测试代码

相等性运算符仅在测试中编译:
```cpp
#if defined(GPU_TEST_UTILS)
```
避免在生产代码中包含仅用于测试的功能。

## 性能考量

### 拷贝开销

拷贝构造和赋值的成本:
- 分配新的 `GrD3DTextureResourceInfo` 对象(小对象,开销低)
- 递增状态对象的引用计数(原子操作)
- 总体开销可接受,因为通常按移动语义传递

### 移动优化

移动操作非常高效:
- `unique_ptr` 移动仅交换指针
- `sk_sp` 移动不改变引用计数
- 适合在容器中使用和返回值优化(RVO)

### 共享状态的同步成本

多个对象共享状态跟踪器:
- 状态更新使用原子操作(在 `GrD3DResourceState` 内部)
- 但避免了为每个表面维护独立状态的内存开销
- 在状态变化频率不高时是好的权衡

### 懒快照避免浪费

`snapTextureResourceInfo` 按需执行:
- 仅在需要时创建副本
- 避免预先计算未使用的数据
- 调用成本:一次结构体拷贝和状态读取

### 内联潜力

简单的访问器函数(如 `isProtected`)易于内联:
- 编译器可以优化为直接字段访问
- 无函数调用开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/gpu/ganesh/GrD3DTypesMinimal.h` | 声明 | 类声明所在头文件 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | 完整的 D3D12 类型定义 |
| `src/gpu/ganesh/d3d/GrD3DResourceState.h` | 依赖 | 资源状态跟踪实现 |
| `src/gpu/ganesh/d3d/GrD3DTypesPriv.h` | 依赖 | 私有类型定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 被使用 | 封装后端表面信息 |
| `src/gpu/ganesh/d3d/GrD3DGpu.cpp` | 被使用 | 处理后端表面 |
