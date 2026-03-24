# SkRasterHandleAllocator

> 源文件: `include/core/SkRasterHandleAllocator.h`

## 概述
SkRasterHandleAllocator 是 Skia 提供的一个可定制的光栅层内存分配器抽象接口。它允许客户端控制画布中光栅层的像素内存分配方式，并将自定义的"句柄"与每个层关联，用于跟踪矩阵/裁剪状态或实现特定的后端集成。

## 架构位置
位于 Skia 核心模块 (`include/core`)，属于 Canvas 和 Surface 子系统的扩展层。它为需要精细控制内存分配的高级用户场景提供了定制点，特别适用于跨进程渲染、硬件加速集成和自定义后端实现。

## 主要类与结构体

### SkRasterHandleAllocator
抽象基类，定义了光栅层分配器的接口契约。

**继承关系**: 纯虚基类，无父类

**设计特点**:
- 虚析构函数，支持多态删除
- 禁用拷贝和赋值，确保分配器唯一性
- 友元 SkBitmapDevice，允许内部访问

### Rec 结构体
```cpp
struct Rec {
    void (*fReleaseProc)(void* pixels, void* ctx);  // 释放回调
    void*   fReleaseCtx;     // 传递给释放回调的上下文
    void*   fPixels;         // 像素数据指针
    size_t  fRowBytes;       // 行字节数
    Handle  fHandle;         // 公共句柄
};
```

**职责**: 封装分配结果，包含像素数据、释放机制和自定义句柄。

**生命周期管理**: 通过 fReleaseProc 实现自定义清理逻辑。

## 公共 API 函数

### 类型定义

#### `Handle`
```cpp
typedef void* Handle;
```
- **功能**: 不透明句柄类型，指向客户端私有数据
- **用途**: 客户端可将任意数据关联到每个层
- **返回**: 通过 `SkCanvas::accessTopRasterHandle()` 访问

### 虚函数接口

#### `allocHandle()`
```cpp
virtual bool allocHandle(const SkImageInfo&, Rec*) = 0;
```
- **功能**: 分配指定 ImageInfo 的像素内存和句柄
- **参数**:
  - `imageInfo`: 描述所需像素格式和尺寸
  - `rec`: 输出参数，填充分配结果
- **返回值**: 成功返回 true，失败返回 false
- **调用时机**:
  - `saveLayer()` 时创建新层
  - 画布初始化时创建基础层（如果未提供 Rec）

#### `updateHandle()`
```cpp
virtual void updateHandle(Handle, const SkMatrix&, const SkIRect&) = 0;
```
- **功能**: 更新句柄以反映当前的矩阵和裁剪区域
- **参数**:
  - `handle`: 要更新的句柄
  - `matrix`: 当前变换矩阵
  - `clip`: 当前裁剪矩形
- **调用时机**:
  - 矩阵变换时（translate, rotate, scale 等）
  - 裁剪区域改变时（clipRect, clipPath 等）

### 静态工厂方法

#### `MakeCanvas()`
```cpp
static std::unique_ptr<SkCanvas> MakeCanvas(
    std::unique_ptr<SkRasterHandleAllocator> allocator,
    const SkImageInfo& info,
    const Rec* rec = nullptr,
    const SkSurfaceProps* props = nullptr
);
```
- **功能**: 创建使用自定义分配器的画布
- **参数**:
  - `allocator`: 分配器实例（转移所有权）
  - `info`: 基础层的 ImageInfo
  - `rec`: 可选的预分配基础层数据
  - `props`: 可选的 Surface 属性
- **返回值**: 新创建的画布

### 私有接口

#### `allocBitmap()`
```cpp
Handle allocBitmap(const SkImageInfo&, SkBitmap*);
```
- **功能**: 内部使用，为 SkBitmapDevice 分配位图
- **访问权限**: 友元 SkBitmapDevice
- **说明**: 实现细节，外部用户无需关注

## 核心概念

### 双重职责
SkRasterHandleAllocator 执行两个关键任务：

1. **内存管理**: 控制像素缓冲区的分配和释放
   - 可使用自定义内存池
   - 可实现共享内存
   - 可对接硬件缓冲区

2. **状态跟踪**: 通过句柄机制跟踪层的图形状态
   - 记录当前的矩阵变换
   - 记录裁剪区域
   - 可用于实现镜像或代理渲染

### 分层架构
画布的层次结构：
```
Canvas
├── Base Layer (通过 MakeCanvas 提供或分配)
└── SaveLayer 1
    └── SaveLayer 2
        └── ...
```

每个层都通过 `allocHandle()` 分配，通过 `fReleaseProc` 释放。

### 句柄的不透明性
Handle 是 `void*` 类型，Skia 不解释其内容：
- 客户端可存储任意数据结构的指针
- 客户端负责句柄指向对象的生命周期
- Skia 仅负责在合适的时机调用回调

## 使用场景

### 基本用法示例
```cpp
class MyAllocator : public SkRasterHandleAllocator {
    struct LayerInfo {
        SkMatrix matrix;
        SkIRect clip;
        void* pixels;
    };

    bool allocHandle(const SkImageInfo& info, Rec* rec) override {
        // 分配像素内存
        size_t rowBytes = info.minRowBytes();
        size_t size = info.computeByteSize(rowBytes);
        void* pixels = malloc(size);

        // 创建私有状态
        LayerInfo* layerInfo = new LayerInfo();
        layerInfo->pixels = pixels;

        // 填充 Rec
        rec->fPixels = pixels;
        rec->fRowBytes = rowBytes;
        rec->fHandle = layerInfo;
        rec->fReleaseProc = [](void* pixels, void* ctx) {
            free(pixels);
            delete static_cast<LayerInfo*>(ctx);
        };
        rec->fReleaseCtx = layerInfo;

        return true;
    }

    void updateHandle(Handle handle, const SkMatrix& matrix,
                      const SkIRect& clip) override {
        LayerInfo* info = static_cast<LayerInfo*>(handle);
        info->matrix = matrix;
        info->clip = clip;
    }
};

// 使用自定义分配器创建画布
auto allocator = std::make_unique<MyAllocator>();
auto canvas = SkRasterHandleAllocator::MakeCanvas(
    std::move(allocator),
    SkImageInfo::MakeN32Premul(800, 600)
);

// 绘图操作
canvas->saveLayer(nullptr, nullptr); // 调用 allocHandle()
canvas->translate(100, 100);          // 调用 updateHandle()
```

### 跨进程渲染
```cpp
class SharedMemoryAllocator : public SkRasterHandleAllocator {
    bool allocHandle(const SkImageInfo& info, Rec* rec) override {
        // 分配共享内存
        SharedMemoryRegion* region = CreateSharedMemory(info.computeByteSize());

        rec->fPixels = region->Map();
        rec->fRowBytes = info.minRowBytes();
        rec->fHandle = region;
        rec->fReleaseProc = [](void* pixels, void* ctx) {
            auto* region = static_cast<SharedMemoryRegion*>(ctx);
            region->Unmap();
            delete region;
        };
        rec->fReleaseCtx = region;
        return true;
    }
    // ...
};
```

### 硬件缓冲区集成
```cpp
class HardwareBufferAllocator : public SkRasterHandleAllocator {
    bool allocHandle(const SkImageInfo& info, Rec* rec) override {
        // 分配 GPU 可访问的缓冲区
        HardwareBuffer* hwBuffer = AllocateHardwareBuffer(info);

        rec->fPixels = hwBuffer->Lock();
        rec->fRowBytes = hwBuffer->Stride();
        rec->fHandle = hwBuffer;
        rec->fReleaseProc = [](void* pixels, void* ctx) {
            auto* hwBuf = static_cast<HardwareBuffer*>(ctx);
            hwBuf->Unlock();
            hwBuf->Release();
        };
        rec->fReleaseCtx = hwBuffer;
        return true;
    }
    // ...
};
```

## 内部实现细节

### 生命周期管理
```
1. Canvas 创建 -> allocHandle() 分配基础层
2. saveLayer()  -> allocHandle() 分配新层
3. 绘图操作    -> updateHandle() 同步状态
4. restore()    -> fReleaseProc() 释放层
5. Canvas 销毁 -> fReleaseProc() 释放基础层
```

### 内存所有权
- **像素数据**: 由客户端分配和释放（通过 fReleaseProc）
- **分配器对象**: 由 Canvas 拥有（MakeCanvas 转移所有权）
- **句柄数据**: 由客户端管理，Skia 不接触

### 回调时机
fReleaseProc 的调用时机：
- `restore()` 恢复到层之前的状态
- Canvas 析构时清理所有未释放的层
- `restoreToCount()` 批量恢复时

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/core/SkImageInfo.h` | 描述像素格式 |
| `SkBitmap` (前向声明) | 内部实现使用 |
| `SkCanvas` (前向声明) | 创建的目标类型 |
| `SkMatrix` (前向声明) | 变换矩阵 |
| `SkSurfaceProps` (前向声明) | Surface 属性 |

### 被依赖的模块
- **SkCanvas**: 使用分配器管理层
- **SkBitmapDevice**: 友元，访问 allocBitmap()
- **高级应用**: 自定义后端集成

## 设计模式与设计决策

### 策略模式
SkRasterHandleAllocator 是策略模式的典型应用：
- 抽象策略：基类定义接口
- 具体策略：客户端实现不同的分配策略
- 上下文：SkCanvas 使用分配器

### 回调模式
使用函数指针而非虚函数处理释放：
- 允许每个 Rec 有不同的释放逻辑
- 避免为每个分配创建对象
- 灵活性更高

### 不透明句柄模式
Handle 作为 `void*` 提供了最大灵活性：
- 客户端可存储任意类型的指针
- 无需 Skia 了解客户端的数据结构
- 避免了模板复杂性

### 工厂模式
MakeCanvas() 是静态工厂方法：
- 封装了复杂的创建逻辑
- 转移分配器所有权
- 返回完全配置好的画布

## 性能考量

### 自定义内存管理的优势
- **池化**: 重用内存块，减少分配/释放开销
- **对齐**: 确保 SIMD 指令的对齐要求
- **局部性**: 将相关层的内存放在一起，提高缓存命中

### 跨进程开销
共享内存方案可能涉及：
- 内存映射操作
- 进程间同步
- 序列化/反序列化开销

### 硬件加速的权衡
硬件缓冲区可能提供：
- GPU 直接访问，避免 CPU->GPU 拷贝
- 但可能增加锁定/解锁开销
- 需要仔细权衡使用场景

## 线程安全

### 非线程安全
SkRasterHandleAllocator 和相关的 Canvas 不是线程安全的：
- 不应在多线程间共享分配器实例
- 每个线程应有独立的 Canvas 和分配器
- updateHandle() 可能在任意绘图操作中被调用

### 多线程策略
如需并发绘图：
- 为每个线程创建独立的 Canvas
- 使用线程安全的内存池实现 allocHandle()
- 合并结果时进行同步

## 注意事项与最佳实践

### Rec 填充要求
- `fPixels` 必须有效且足够大
- `fRowBytes` 必须至少为 `info.minRowBytes()`
- `fReleaseProc` 可为 nullptr（如不需清理）
- `fHandle` 可为任意值，包括 nullptr

### 句柄访问
```cpp
// 获取当前层的句柄
void* handle = canvas->accessTopRasterHandle();
MyLayerInfo* info = static_cast<MyLayerInfo*>(handle);
```

### 错误处理
- `allocHandle()` 返回 false 时，Canvas 创建/saveLayer 失败
- 应确保分配成功，否则可能导致渲染异常

### 内存泄漏预防
- 确保 fReleaseProc 正确释放所有资源
- 注意 fReleaseCtx 和 fPixels 可能指向不同对象
- 使用智能指针或 RAII 封装可提高安全性

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkCanvas.h` | 使用分配器，提供 accessTopRasterHandle() |
| `include/core/SkSurface.h` | 可能也支持自定义分配器 |
| `src/core/SkBitmapDevice.h` | 友元，内部实现 |
| `include/core/SkImageInfo.h` | 描述分配需求 |
