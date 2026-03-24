# BackendTexturePriv

> 源文件
> - src/gpu/graphite/BackendTexturePriv.h

## 概述

`BackendTexturePriv` 是 Graphite 渲染系统中用于管理后端特定纹理数据的私有接口类。它提供了创建和访问 `BackendTexture` 对象内部数据的工厂方法和访问器，支持 Vulkan、Metal、D3D12 等不同后端的纹理抽象。该模块采用类型擦除技术隐藏后端差异，使上层代码可以统一处理不同 GPU API 的纹理对象。

## 架构位置

```
Graphite Texture System
├── BackendTexture (公共接口)
│   └── AnyBackendTextureData (类型擦除存储)
└── BackendTexturePriv (本类) ← 私有访问接口
    └── BackendTextureData (抽象数据基类)
        ├── VulkanTextureData
        ├── MetalTextureData
        └── DawnTextureData
```

## 主要类与结构体

### BackendTextureData 抽象基类

```cpp
class BackendTextureData
```

**职责**：定义后端纹理数据的通用接口

**关键成员**：

| 成员 | 类型 | 说明 |
|------|------|------|
| `type()` | `virtual skgpu::BackendApi` | 返回后端 API 类型（仅 Debug） |
| `copyTo()` | `virtual void` | 拷贝数据到目标存储 |
| `equal()` | `virtual bool` | 比较两个纹理数据是否相等 |

**虚析构函数**：
```cpp
virtual ~BackendTextureData();
```
确保多态删除安全。

### BackendTexturePriv 工厂类

```cpp
class BackendTexturePriv
```

**设计模式**：静态工厂 + 友元访问器

**成员函数表**：

| 函数 | 参数 | 返回类型 | 说明 |
|------|------|---------|------|
| `Make<T>()` | 尺寸、纹理信息、数据 | `BackendTexture` | 创建纹理对象 |
| `GetData()` | `const BackendTexture&` | `const BackendTextureData*` | 获取只读数据 |
| `GetData()` | `BackendTexture*` | `BackendTextureData*` | 获取可写数据 |

## 公共 API 函数

### 1. 工厂方法

```cpp
template <typename SomeBackendTextureData>
static BackendTexture Make(
    SkISize dimensions,
    TextureInfo info,
    const SomeBackendTextureData& textureData
)
```

**功能**：创建包含特定后端数据的 `BackendTexture` 对象

**模板参数**：
- `SomeBackendTextureData`：具体后端的纹理数据类型（如 `VulkanTextureData`）

**参数**：
- `dimensions`：纹理尺寸（宽高）
- `info`：纹理信息（格式、用法、多重采样等）
- `textureData`：后端特定的纹理数据（包含原生句柄）

**返回值**：包含后端数据的 `BackendTexture` 对象

**使用示例**：
```cpp
VulkanTextureData vkData{vkImage, vkImageView, vkAlloc};
BackendTexture tex = BackendTexturePriv::Make(
    {1024, 768},
    textureInfo,
    vkData
);
```

### 2. 数据访问器（常量版本）

```cpp
static const BackendTextureData* GetData(const BackendTexture& info)
```

**功能**：获取纹理对象内部存储的只读后端数据指针

**返回值**：指向 `BackendTextureData` 的常量指针

**用途**：
- 后端实现提取纹理句柄
- 纹理信息查询
- 绑定纹理到命令缓冲

### 3. 数据访问器（可写版本）

```cpp
static BackendTextureData* GetData(BackendTexture* info)
```

**功能**：获取纹理对象内部存储的可写后端数据指针

**前提条件**：`info` 不能为 `nullptr`（通过 `SkASSERT` 检查）

**返回值**：指向 `BackendTextureData` 的可写指针

**用途**：
- 更新纹理状态
- 后端特定的修改操作
- 纹理包装（wrapping）

## 内部实现细节

### 类型擦除机制

`BackendTexture` 使用 `std::unique_ptr<BackendTextureData>` 存储数据：

```cpp
// BackendTexture 内部（概念代码）
class BackendTexture {
private:
    SkISize fDimensions;
    TextureInfo fInfo;
    std::unique_ptr<BackendTextureData> fTextureData;
};
```

### copyTo() 虚函数

```cpp
virtual void copyTo(AnyBackendTextureData& dstData) const = 0
```

**功能**：支持 `BackendTexture` 的拷贝构造和赋值操作

**实现要求**：子类必须实现深拷贝逻辑

**典型实现**：
```cpp
void VulkanTextureData::copyTo(AnyBackendTextureData& dst) const {
    dst.emplace<VulkanTextureData>(*this);
}
```

### equal() 虚函数

```cpp
virtual bool equal(const BackendTextureData* that) const = 0
```

**功能**：比较两个纹理数据是否引用相同的底层纹理对象

**用途**：
- 纹理缓存查找
- 去重优化
- 纹理别名检测

**实现示例**：
```cpp
bool VulkanTextureData::equal(const BackendTextureData* that) const {
    auto* vkThat = static_cast<const VulkanTextureData*>(that);
    return fImage == vkThat->fImage;  // 比较 VkImage 句柄
}
```

### Debug 类型检查

```cpp
#if defined(SK_DEBUG)
    virtual skgpu::BackendApi type() const = 0;
#endif
```

**目的**：
- Debug 构建中验证类型安全
- 捕获跨后端使用错误
- Release 构建中移除以减少开销

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `BackendTexture` | 公共纹理接口 |
| `TextureInfo` | 纹理格式和配置 |
| `SkISize` | 纹理尺寸表示 |
| `skgpu::BackendApi` | 后端 API 类型枚举 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `VulkanTexture` | 创建和操作 Vulkan 纹理 |
| `MetalTexture` | 创建和操作 Metal 纹理 |
| `TextureProxy` | 包装后端纹理 |
| `Context` | 跨后端纹理创建 |

## 设计模式与设计决策

### 1. 类型擦除（Type Erasure）

通过虚函数隐藏后端差异：
```
BackendTextureData (抽象)
    ↓
VulkanTextureData (具体实现：VkImage + VkImageView)
MetalTextureData (具体实现：id<MTLTexture>)
```

**优点**：
- 公共 API 无需模板化
- 支持运行时后端选择
- 简化跨模块边界

### 2. 友元访问器模式

`BackendTexturePriv` 作为 `BackendTexture` 的友元：
```cpp
friend class BackendTexturePriv;
```

**设计意图**：
- 公共接口保持简洁
- 内部数据受保护
- 后端实现可访问原生句柄

### 3. 双重访问器

提供 `const` 和非 `const` 两个版本的 `GetData()`：
```cpp
static const BackendTextureData* GetData(const BackendTexture&);
static BackendTextureData* GetData(BackendTexture*);
```

**用途区分**：
- 只读访问：查询纹理信息
- 可写访问：更新纹理状态

**安全性**：
- 非 const 版本要求指针非空（`SkASSERT`）
- 保持常量正确性（const-correctness）

### 4. 模板工厂方法

```cpp
template <typename SomeBackendTextureData>
static BackendTexture Make(...)
```

**优势**：
- 编译期类型检查
- 避免显式转型
- 支持完美转发

### 5. 相等性比较

`equal()` 虚函数支持纹理对象的值语义比较：
- 不是比较指针地址
- 比较底层资源句柄
- 支持纹理缓存和别名检测

## 性能考量

### 1. 内联优化

所有静态方法定义在头文件中，支持编译器内联：
```cpp
static BackendTexture Make(...) {
    return BackendTexture(dimensions, info, textureData);
}
```

### 2. Debug/Release 分离

类型检查仅在 Debug 构建存在：
```cpp
#if defined(SK_DEBUG)
    virtual skgpu::BackendApi type() const = 0;
#endif
```

- **Debug**：类型安全验证
- **Release**：零运行时开销

### 3. 虚函数开销

**虚函数表成本**：
- 每个对象 8 字节 vtable 指针
- 虚函数调用 ~5-10 纳秒

**可接受原因**：
- 纹理对象相对较少（成百上千级别，非百万级别）
- 创建和绑定操作不在热路径
- 类型安全和可维护性收益大于开销

### 4. 拷贝语义优化

`copyTo()` 支持高效拷贝：
- 使用移动语义（`emplace`）
- 避免临时对象分配
- 保持浅拷贝语义（共享底层资源）

### 5. 相等性比较性能

`equal()` 通常只比较句柄：
```cpp
return fImage == that->fImage;  // 指针/整数比较
```

O(1) 时间复杂度，支持快速纹理缓存查找。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/graphite/BackendTexture.h` | 公共接口 | 用户可见的纹理类 |
| `include/gpu/graphite/TextureInfo.h` | 配置 | 纹理格式和用法 |
| `include/core/SkSize.h` | 依赖 | 尺寸表示 |
| `src/gpu/graphite/vk/VulkanTexture.h` | 具体实现 | Vulkan 纹理数据 |
| `src/gpu/graphite/mtl/MtlTexture.h` | 具体实现 | Metal 纹理数据 |
| `src/gpu/graphite/dawn/DawnTexture.h` | 具体实现 | Dawn 纹理数据 |
| `src/gpu/graphite/TextureProxy.h` | 使用者 | 纹理代理包装 |
| `src/gpu/graphite/Context.h` | 使用者 | 跨后端纹理管理 |
| `src/gpu/graphite/Image_Graphite.h` | 使用者 | 图像与纹理绑定 |
