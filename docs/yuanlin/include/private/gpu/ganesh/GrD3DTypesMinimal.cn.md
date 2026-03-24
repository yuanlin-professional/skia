# GrD3DTypesMinimal

> 源文件: `include/private/gpu/ganesh/GrD3DTypesMinimal.h`

## 概述
GrD3DTypesMinimal 提供了 Direct3D 12 类型的最小化定义,无需包含完整的 d3d12.h 头文件。它定义了 GrD3DBackendSurfaceInfo 结构体,用于在 GrBackendTexture 和 GrBackendRenderTarget 中存储 Direct3D 后端图像信息,实现了资源状态的共享追踪机制。

## 架构位置
该文件位于 Skia 的 GPU 后端 Ganesh 子系统的 Direct3D 支持层中。它是 D3D 后端类型系统的最小化接口层,位于 Skia 与 Direct3D API 之间的抽象层底部,为上层的后端纹理和渲染目标提供类型支持。

## 主要类与结构体

### GrD3DBackendSurfaceInfo
用于存储 Direct3D 后端表面的实际信息,是 GrBackendTexture 和 GrBackendRenderTarget 的内部数据持有者。

**继承关系**: 无(普通结构体)

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fTextureResourceInfo | std::unique_ptr<GrD3DTextureResourceInfo> | 纹理资源信息的独占指针 |
| fResourceState | sk_sp<GrD3DResourceState> | 资源状态的共享引用计数指针 |

## 公共 API 函数

### 构造函数与析构函数

#### `GrD3DBackendSurfaceInfo(const GrD3DTextureResourceInfo& info, sk_sp<GrD3DResourceState> state)`
- **功能**: 从纹理资源信息和资源状态构造表面信息对象
- **参数**:
  - `info`: 纹理资源的详细信息
  - `state`: 资源状态的共享指针,用于多用户间同步状态
- **返回值**: 构造的对象

#### `~GrD3DBackendSurfaceInfo()`
- **功能**: 析构函数,清理资源
- **参数**: 无
- **返回值**: 无

### 拷贝与移动操作

#### `GrD3DBackendSurfaceInfo(const GrD3DBackendSurfaceInfo&)`
- **功能**: 拷贝构造函数,创建表面信息的副本
- **参数**: 源对象的常量引用
- **返回值**: 构造的对象

#### `GrD3DBackendSurfaceInfo& operator=(const GrD3DBackendSurfaceInfo&)`
- **功能**: 拷贝赋值操作符
- **参数**: 源对象的常量引用
- **返回值**: 当前对象的引用

#### `GrD3DBackendSurfaceInfo(GrD3DBackendSurfaceInfo&&)`
- **功能**: 移动构造函数,高效转移资源所有权
- **参数**: 源对象的右值引用
- **返回值**: 构造的对象

#### `GrD3DBackendSurfaceInfo& operator=(GrD3DBackendSurfaceInfo&&)`
- **功能**: 移动赋值操作符
- **参数**: 源对象的右值引用
- **返回值**: 当前对象的引用

### 状态管理函数

#### `void setResourceState(GrD3DResourceStateEnum state)`
- **功能**: 设置 D3D 资源的当前状态(对应 D3D12_RESOURCE_STATES)
- **参数**: `state` - 新的资源状态枚举值
- **返回值**: 无

#### `sk_sp<GrD3DResourceState> getResourceState() const`
- **功能**: 获取资源状态的共享指针
- **参数**: 无
- **返回值**: 指向资源状态对象的智能指针

### 信息查询函数

#### `GrD3DTextureResourceInfo snapTextureResourceInfo() const`
- **功能**: 创建纹理资源信息的快照副本
- **参数**: 无
- **返回值**: 纹理资源信息的副本,包含当前时刻的资源状态

#### `bool isProtected() const`
- **功能**: 查询纹理是否为受保护内容(如 DRM 保护的视频)
- **参数**: 无
- **返回值**: true 表示受保护,false 表示普通纹理

### 测试辅助函数

#### `bool operator==(const GrD3DBackendSurfaceInfo& that) const`
- **功能**: 比较两个表面信息对象是否相等(仅在测试构建中可用)
- **参数**: `that` - 要比较的另一个对象
- **返回值**: 相等返回 true,否则返回 false
- **可用性**: 仅在 GPU_TEST_UTILS 定义时编译

## 内部实现细节

### 资源状态共享机制
GrD3DBackendSurfaceInfo 的核心设计是通过引用计数的 GrD3DResourceState 对象来追踪 D3D12_RESOURCE_STATES:

```cpp
sk_sp<GrD3DResourceState> fResourceState;
```

这个共享指针允许:
1. 内部的 GrD3DTextureResource 和外部的 GrBackendTexture 共享同一个状态对象
2. 任何一方更新资源状态,所有持有者都能看到最新状态
3. 避免状态同步的复杂性和不一致问题

### 快照机制
`snapTextureResourceInfo()` 方法创建一个包含当前资源状态的快照:
- 客户端调用 `getD3DTextureInfo` 时不会直接暴露内部数据
- 返回的快照包含当前时刻的完整纹理信息
- 快照与原始对象解耦,避免了外部修改内部状态的风险

### 最小化依赖设计
文件只包含 `<dxgiformat.h>`,避免了对完整 `d3d12.h` 的依赖:
- 减少编译时间
- 降低头文件包含的复杂性
- 只暴露必要的类型定义(如 ID3D12Resource 前向声明)

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRefCnt | 智能指针 sk_sp 的基础 |
| dxgiformat.h | DXGI 格式枚举定义 |
| GrTypes | Ganesh GPU 通用类型 |
| ID3D12Resource | D3D12 资源接口(前向声明) |
| GrD3DResourceState | D3D 资源状态跟踪类 |
| GrD3DTextureResourceInfo | 纹理资源详细信息结构 |

### 被依赖的模块
- GrBackendTexture: 使用此类型存储 D3D 后端纹理信息
- GrBackendRenderTarget: 使用此类型存储 D3D 后端渲染目标信息
- GrD3DGpu: D3D GPU 实现,处理后端表面
- GrD3DTextureResource: 内部纹理资源实现
- Skia D3D 后端的其他组件

## 设计模式与设计决策

### PIMPL(指针实现)模式
使用 `std::unique_ptr<GrD3DTextureResourceInfo>` 隐藏完整的资源信息实现细节,允许:
- 前向声明,减少头文件依赖
- 灵活修改内部实现而不影响 API
- 控制数据的复制和移动语义

### 观察者模式的变体
通过共享的 GrD3DResourceState 对象,多个使用者可以观察和更新同一资源的状态,这是观察者模式的一种实现形式。

### 值语义与引用语义混合
- GrD3DTextureResourceInfo 使用独占所有权(unique_ptr)
- GrD3DResourceState 使用共享所有权(sk_sp)

这种设计平衡了资源管理的效率和状态共享的需求。

### 快照隔离
提供快照方法而非直接访问内部数据,实现了数据隔离,保护内部状态免受外部修改。

## 性能考量

### 智能指针开销
使用 sk_sp 和 unique_ptr 引入了少量的引用计数和指针间接访问开销,但这些开销相比 GPU 操作本身可以忽略不计。

### 状态共享优化
通过引用计数共享资源状态,避免了状态复制和同步的开销,多个对象可以高效地访问和更新同一状态。

### 移动语义优化
提供了移动构造函数和移动赋值操作符,在传递大对象时避免不必要的深拷贝,提升性能。

### 最小化编译依赖
不包含 d3d12.h 大大减少了编译时间,这对于大型项目的增量编译非常重要。

## 平台相关说明

### Direct3D 12 专用
此文件完全针对 Windows 平台的 Direct3D 12 API:
- 依赖 DXGI 格式定义
- 封装 D3D12_RESOURCE_STATES 状态
- 仅在 Windows 构建中使用

### 受保护内容支持
`isProtected()` 方法支持 Windows 的内容保护机制(如 PlayReady DRM),这是 D3D 平台特有的功能。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/GrBackendSurface.h | 使用 GrD3DBackendSurfaceInfo 存储 D3D 后端信息 |
| src/gpu/ganesh/d3d/GrD3DResourceState.h | 资源状态类定义 |
| src/gpu/ganesh/d3d/GrD3DTextureResourceInfo.h | 纹理资源信息结构定义 |
| src/gpu/ganesh/d3d/GrD3DTexture.h | D3D 纹理实现 |
| src/gpu/ganesh/d3d/GrD3DGpu.h | D3D GPU 后端实现 |
| include/gpu/d3d/GrD3DTypes.h | 完整的 D3D 类型定义(依赖 d3d12.h) |
