# GrGpuBuffer

> 源文件: src/gpu/ganesh/GrGpuBuffer.h, src/gpu/ganesh/GrGpuBuffer.cpp

## 概述

`GrGpuBuffer` 是 Skia Ganesh GPU 后端中表示 GPU 缓冲区对象的抽象基类。它继承自 `GrGpuResource` 和 `GrBuffer`,为顶点缓冲区、索引缓冲区、Uniform 缓冲区以及传输缓冲区提供统一的接口。该类封装了缓冲区的映射、更新、清零等操作,并支持不同的访问模式以优化性能。

主要功能:
- 统一的缓冲区类型抽象 (顶点、索引、Uniform、传输等)
- 内存映射 (Map/Unmap) 接口用于 CPU 访问
- 数据更新接口支持完全/部分更新
- Scratch Key 机制支持动态缓冲区复用
- 与资源缓存集成实现自动内存管理

## 架构位置

`GrGpuBuffer` 位于 Ganesh 资源管理层,是 GPU 缓冲区对象的抽象接口:

1. **继承层次**
   ```
   GrGpuResource (资源管理)
        └── GrGpuBuffer (缓冲区抽象)
                ├── GrD3DBuffer (D3D 实现)
                ├── GrGLBuffer (OpenGL 实现)
                ├── GrVkBuffer (Vulkan 实现)
                └── GrMtlBuffer (Metal 实现)
   ```

2. **与其他模块的关系**
   - `GrOpsRenderPass` 使用缓冲区绑定顶点和索引数据
   - `GrGpuBufferWriteTask` 管理缓冲区更新任务
   - `GrResourceProvider` 负责缓冲区的创建和分配
   - `GrResourceCache` 管理缓冲区的生命周期和复用

3. **缓冲区类型**
   - `kVertex`: 顶点缓冲区
   - `kIndex`: 索引缓冲区
   - `kDrawIndirect`: 间接绘制缓冲区
   - `kXferCpuToGpu`: CPU 到 GPU 传输缓冲区
   - `kXferGpuToCpu`: GPU 到 CPU 传输缓冲区
   - `kUniform`: Uniform 缓冲区

## 主要类与结构体

### 继承关系

```
GrIORef<GrGpuResource>
    └── GrGpuResource
            └── GrGpuBuffer (同时继承 GrBuffer)
                    ├── GrD3DBuffer
                    ├── GrGLBuffer
                    ├── GrVkBuffer
                    └── GrMtlBuffer
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMapPtr` | `void*` | 映射后的内存指针,未映射时为 nullptr |
| `fSizeInBytes` | `size_t` | 缓冲区大小(字节) |
| `fAccessPattern` | `GrAccessPattern` | 访问模式 (静态/动态/流式) |
| `fIntendedType` | `GrGpuBufferType` | 缓冲区预期用途 |

### GrAccessPattern 枚举

```cpp
enum GrAccessPattern {
    kDynamic_GrAccessPattern,  // 动态访问,可被缓存复用
    kStatic_GrAccessPattern,   // 静态访问,创建后很少修改
    kStream_GrAccessPattern    // 流式访问,每帧更新
};
```

### GrGpuBufferType 枚举

```cpp
enum class GrGpuBufferType {
    kVertex,           // 顶点缓冲区
    kIndex,            // 索引缓冲区
    kDrawIndirect,     // 间接绘制参数缓冲区
    kXferCpuToGpu,     // CPU 到 GPU 传输
    kXferGpuToCpu,     // GPU 到 CPU 传输
    kUniform           // Uniform 缓冲区
};
```

### MapType 枚举 (内部)

```cpp
enum class MapType {
    kRead,            // 只读映射
    kWriteDiscard     // 写入映射,丢弃原内容
};
```

## 公共 API 函数

### 工厂方法

```cpp
// 计算动态缓冲区的 Scratch Key
// 仅适用于 kDynamic_GrAccessPattern 的缓冲区
static void ComputeScratchKeyForDynamicBuffer(
    size_t size,
    GrGpuBufferType type,
    skgpu::ScratchKey* key);
```

### 属性查询

```cpp
// 获取访问模式
GrAccessPattern accessPattern() const;

// 获取缓冲区大小
size_t size() const final;

// 获取预期类型
GrGpuBufferType intendedType() const;

// 检查是否为 CPU 缓冲区(始终返回 false)
bool isCpuBuffer() const final;
```

### 引用计数

```cpp
// 增加引用计数
void ref() const final;

// 减少引用计数
void unref() const final;
```

### 内存映射

```cpp
// 将缓冲区映射到 CPU 可访问的内存
// XferGpuToCpu 类型: 只读映射
// 其他类型: 写入映射(丢弃原内容)
// 返回映射后的指针,失败返回 nullptr
void* map();

// 取消映射
void unmap();

// 检查缓冲区是否已映射
bool isMapped() const;
```

### 数据更新

```cpp
// 将缓冲区内容清零
// 不支持 XferGpuToCpu 类型
// 缓冲区必须未映射
// 成功返回 true
bool clearToZero();

// 更新缓冲区数据
// src: 源数据指针
// offset: 起始偏移(字节)
// size: 更新大小(字节)
// preserve: 是否保留未更新部分的数据
//   - false: 其他数据变为未定义,性能更好
//   - true: 保留其他数据,需要对齐
// 不支持 XferGpuToCpu 类型,缓冲区必须未映射
bool updateData(const void* src, size_t offset, size_t size, bool preserve);
```

## 内部实现细节

### 映射机制

```cpp
void* GrGpuBuffer::map() {
    if (wasDestroyed()) return nullptr;

    if (!fMapPtr) {
        // 根据缓冲区类型确定映射类型
        MapType mapType = (intendedType() == kXferGpuToCpu)
                          ? MapType::kRead
                          : MapType::kWriteDiscard;
        this->onMap(mapType);  // 调用子类实现
    }
    return fMapPtr;
}

void GrGpuBuffer::unmap() {
    if (wasDestroyed()) return;
    SkASSERT(fMapPtr);

    MapType mapType = this->mapType();
    this->onUnmap(mapType);  // 调用子类实现
    fMapPtr = nullptr;
}
```

### MapType 推导

```cpp
MapType mapType() const {
    // XferGpuToCpu: 只读映射
    // 其他类型: 写入映射(丢弃)
    return (intendedType() == GrGpuBufferType::kXferGpuToCpu)
           ? MapType::kRead
           : MapType::kWriteDiscard;
}
```

### 数据更新实现

```cpp
bool GrGpuBuffer::updateData(const void* src, size_t offset,
                              size_t size, bool preserve) {
    SkASSERT(!isMapped());
    SkASSERT(size > 0 && offset + size <= fSizeInBytes);
    SkASSERT(src);

    if (wasDestroyed()) return false;

    // 检查对齐要求
    if (preserve) {
        size_t alignment = getGpu()->caps()->bufferUpdateDataPreserveAlignment();
        if (!SkIsAlign(offset, alignment) || !SkIsAlign(size, alignment)) {
            return false;
        }
    }

    // XferGpuToCpu 类型不支持更新
    if (intendedType() == GrGpuBufferType::kXferGpuToCpu) {
        return false;
    }

    return this->onUpdateData(src, offset, size, preserve);
}
```

### 清零实现

```cpp
bool GrGpuBuffer::clearToZero() {
    SkASSERT(!isMapped());

    if (wasDestroyed()) return false;

    // XferGpuToCpu 类型不支持清零
    if (intendedType() == GrGpuBufferType::kXferGpuToCpu) {
        return false;
    }

    return this->onClearToZero();
}
```

### Scratch Key 计算

```cpp
void GrGpuBuffer::ComputeScratchKeyForDynamicBuffer(
    size_t size, GrGpuBufferType type, skgpu::ScratchKey* key) {

    static const skgpu::ScratchKey::ResourceType kType =
        skgpu::ScratchKey::GenerateResourceType();

    // Key 格式: [type][size_low][size_high (仅64位)]
    int keySize = 1 + (sizeof(size_t) + 3) / 4;
    skgpu::ScratchKey::Builder builder(key, kType, keySize);

    builder[0] = SkToU32(type);
    builder[1] = (uint32_t)size;
    if (sizeof(size_t) > 4) {
        builder[2] = (uint32_t)((uint64_t)size >> 32);
    }
}

void GrGpuBuffer::computeScratchKey(skgpu::ScratchKey* key) const {
    // 仅动态访问模式的缓冲区可被复用
    if (fAccessPattern == kDynamic_GrAccessPattern) {
        ComputeScratchKeyForDynamicBuffer(fSizeInBytes, fIntendedType, key);
    }
}
```

### 资源类型报告

```cpp
size_t onGpuMemorySize() const override {
    return fSizeInBytes;
}

const char* getResourceType() const override {
    return "Buffer Object";
}

void onSetLabel() override {
    // 由子类实现,更新 GPU 对象的标签
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpuResource` | 基类,提供缓存和生命周期管理 |
| `GrBuffer` | 缓冲区接口定义 |
| `GrGpu` | 访问 GPU 驱动和能力查询 |
| `GrCaps` | 查询对齐要求等能力 |
| `skgpu::ScratchKey` | Scratch 键系统 |
| `GrTypesPriv.h` | Ganesh 内部类型定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrGLBuffer` | OpenGL 缓冲区实现 |
| `GrVkBuffer` | Vulkan 缓冲区实现 |
| `GrD3DBuffer` | Direct3D 缓冲区实现 |
| `GrMtlBuffer` | Metal 缓冲区实现 |
| `GrResourceProvider` | 创建和分配缓冲区 |
| `GrOpsRenderPass` | 绑定和使用缓冲区 |
| `GrGpuBufferWriteTask` | 缓冲区更新任务 |

## 设计模式与设计决策

### 设计模式

1. **模板方法模式 (Template Method)**
   - `map()`, `unmap()`, `updateData()` 定义流程框架
   - `onMap()`, `onUnmap()`, `onUpdateData()` 由子类实现
   - 基类处理错误检查和状态管理

2. **策略模式 (Strategy Pattern)**
   - `GrAccessPattern` 定义访问策略
   - 不同策略影响缓存行为和性能优化

3. **适配器模式 (Adapter Pattern)**
   - 统一不同 GPU API 的缓冲区接口
   - OpenGL, Vulkan, Metal 等差异被隐藏

4. **双重继承设计**
   - 继承 `GrGpuResource` 获得缓存管理能力
   - 继承 `GrBuffer` 获得缓冲区接口
   - 实现接口和实现分离

### 关键设计决策

1. **为何区分 MapType?**
   - `kRead`: GPU 到 CPU 传输,保持原内容
   - `kWriteDiscard`: CPU 到 GPU 传输,丢弃原内容优化性能
   - 根据缓冲区类型自动推导,简化接口

2. **为何只有动态缓冲区可复用?**
   - `kDynamic`: 频繁更新,适合复用
   - `kStatic`: 创建后不变,复用意义不大
   - `kStream`: 每帧更新,生命周期短,不需要缓存

3. **preserve 参数的权衡**
   - `false`: 驱动可以完全重新分配内存,性能最佳
   - `true`: 需要部分更新时使用,但有对齐要求
   - 对齐要求取决于硬件能力

4. **为何 XferGpuToCpu 不支持写入操作?**
   - 该类型缓冲区用于从 GPU 读取数据
   - 不支持 `clearToZero()` 和 `updateData()`
   - 防止误用,明确语义

5. **映射状态管理**
   - `fMapPtr` 存储映射指针
   - 重复 `map()` 返回同一指针(幂等)
   - 必须 `unmap()` 后才能进行其他操作

6. **Scratch Key 包含大小和类型**
   - 相同大小和类型的缓冲区可以复用
   - 避免频繁创建相同规格的缓冲区
   - 减少 GPU 驱动调用

## 性能考量

### 访问模式优化

1. **kDynamic_GrAccessPattern**
   - 启用 Scratch 缓存,复用缓冲区
   - 适合每帧更新少数次的缓冲区
   - 例如: 动态几何体,粒子系统

2. **kStatic_GrAccessPattern**
   - 驱动可以优化为 GPU 侧内存
   - 避免不必要的同步
   - 例如: 静态模型数据

3. **kStream_GrAccessPattern**
   - 驱动知道数据很快过时
   - 可以使用双缓冲或环形缓冲
   - 例如: UI 文本每帧重建

### 映射开销

1. **写入映射 (kWriteDiscard)**
   - 丢弃原内容,驱动可以避免同步
   - 可能分配新的内存页
   - 最小化 GPU-CPU 同步点

2. **只读映射 (kRead)**
   - 可能需要等待 GPU 完成写入
   - 引入同步点,应尽量避免
   - 仅用于 readback 场景

### 更新策略

1. **完全更新 (preserve=false)**
   - 驱动可以直接替换内存
   - 避免 read-modify-write
   - 优先使用

2. **部分更新 (preserve=true)**
   - 需要对齐到硬件要求
   - 可能需要 RMW 操作
   - 仅在必要时使用

### 缓存复用

- 动态缓冲区通过 Scratch Key 复用
- 减少缓冲区创建和销毁开销
- 减少 GPU 内存碎片

### 内存对齐

- 部分更新的对齐要求通过 `GrCaps` 查询
- 未对齐的更新会被拒绝
- 避免硬件性能陷阱

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 基类 | 资源管理基类 |
| `src/gpu/ganesh/GrBuffer.h` | 基类 | 缓冲区接口定义 |
| `src/gpu/ganesh/gl/GrGLBuffer.h` | 子类 | OpenGL 实现 |
| `src/gpu/ganesh/vk/GrVkBuffer.h` | 子类 | Vulkan 实现 |
| `src/gpu/ganesh/d3d/GrD3DBuffer.h` | 子类 | Direct3D 实现 |
| `src/gpu/ganesh/mtl/GrMtlBuffer.h` | 子类 | Metal 实现 |
| `src/gpu/ganesh/GrResourceProvider.h` | 使用 | 缓冲区创建和分配 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 使用 | 渲染通道中绑定缓冲区 |
| `src/gpu/ganesh/GrGpuBufferWriteTask.h` | 使用 | 异步缓冲区更新任务 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询 |
