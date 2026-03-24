# GrDeferredProxyUploader

> 源文件
> - src/gpu/ganesh/GrDeferredProxyUploader.h

## 概述

`GrDeferredProxyUploader` 是 Skia Ganesh 渲染引擎中用于异步纹理上传的辅助类，专门用于支持多线程纹理生成场景。该类配合工作线程使用，允许在后台线程中生成像素数据，然后在主线程的刷新阶段将数据上传到GPU纹理。

该模块广泛应用于软件裁剪遮罩（software clip masks）和软件路径渲染器（software path renderer）等场景，这些场景需要CPU密集型的光栅化操作，通过多线程可以显著提升性能。

## 架构位置

`GrDeferredProxyUploader` 位于 Skia 多线程纹理上传架构中：

```
Skia Threaded Texture Upload Architecture
├── Main Thread (主线程)
│   ├── GrOp (图形操作)
│   ├── GrOpList (操作列表)
│   ├── GrTextureProxy (纹理代理)
│   └── GrOpFlushState (刷新状态)
├── Worker Thread (工作线程)
│   ├── Task (任务)
│   ├── GrDeferredProxyUploader ← 当前模块
│   │   ├── Payload Data (载荷数据 T)
│   │   └── SkAutoPixmapStorage (像素存储)
│   └── Rasterization (光栅化)
└── GPU Upload (GPU上传)
    └── GrDeferredTextureUploadFn (延迟上传函数)
```

该模块在架构中的职责：
- 存储工作线程需要的载荷数据
- 管理像素数据的生成和存储
- 协调主线程和工作线程的同步
- 调度ASAP上传到刷新状态

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDeferredProxyUploader` | `SkNoncopyable` | 基础上传器类 |
| `GrTDeferredProxyUploader<T>` | `GrDeferredProxyUploader` | 模板上传器类，支持自定义载荷 |

### GrDeferredProxyUploader 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPixels` | `SkAutoPixmapStorage` | 像素数据存储 |
| `fPixelsReady` | `SkSemaphore` | 像素准备就绪信号量 |
| `fScheduledUpload` | `bool` | 是否已调度上传 |
| `fWaited` | `bool` | 是否已等待信号量 |

### GrTDeferredProxyUploader<T> 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `std::unique_ptr<T>` | 载荷数据（如路径、裁剪区域） |

## 公共 API 函数

### 构造函数
```cpp
GrDeferredProxyUploader();
```
创建上传器实例，初始化标志为false。

### 析构函数
```cpp
virtual ~GrDeferredProxyUploader();
```
等待像素准备完成（通过 `wait()`），确保工作线程完成。

### scheduleUpload
```cpp
void scheduleUpload(GrOpFlushState* flushState, GrTextureProxy* proxy);
```
调度上传任务到刷新状态。

**参数说明：**
- `flushState`: 操作刷新状态
- `proxy`: 目标纹理代理

**实现逻辑：**
1. 检查是否已调度（避免重复上传）
2. 创建上传回调函数
3. 等待像素准备就绪（`wait()`）
4. 如果像素数据有效，调用 `writePixelsFn` 上传
5. 通知代理释放上传器（`resetDeferredUploader()`）
6. 添加为ASAP上传

### signalAndFreeData
```cpp
void signalAndFreeData();
```
工作线程调用，释放载荷数据并发出信号。

**调用时机：** 工作线程完成像素生成后

### getPixels
```cpp
SkAutoPixmapStorage* getPixels();
```
获取像素存储指针，供工作线程填充数据。

### wait
```cpp
void wait();
```
等待像素准备就绪（protected方法）。

## 内部实现细节

### 完整的使用流程

```cpp
// 步骤1: 主线程创建上传器和代理
auto uploader = sk_make_sp<GrTDeferredProxyUploader<SkPath>>(path);
auto proxy = proxyProvider->createTextureProxy(...);
proxy->texPriv().setDeferredUploader(uploader);

// 步骤2: 创建并提交工作线程任务
SkTaskGroup* taskGroup = context->priv().getTaskGroup();
taskGroup->add([uploader] {
    // 工作线程中
    SkAutoPixmapStorage* pixmap = uploader->getPixels();
    pixmap->alloc(SkImageInfo::MakeN32Premul(width, height));

    // 执行CPU密集型操作（如路径光栅化）
    SkCanvas canvas(pixmap->writable());
    canvas.drawPath(uploader->data(), paint);

    // 通知完成并释放数据
    uploader->signalAndFreeData();
});

// 步骤3: 主线程创建引用代理的操作
auto op = MyOp::Make(proxy);
opList->addOp(op);

// 步骤4: 刷新时
opList->instantiate(resourceProvider);  // 实例化代理
uploader->scheduleUpload(flushState, proxy);

// 步骤5: ASAP上传执行
// - 等待信号量（确保工作线程完成）
// - 上传像素到纹理
// - 释放上传器

// 步骤6: 操作执行
// - 绘制使用已上传的纹理
```

### scheduleUpload 实现

```cpp
void scheduleUpload(GrOpFlushState* flushState, GrTextureProxy* proxy) {
    if (fScheduledUpload) {
        // 多个引用可能导致重复调用
        return;
    }

    auto uploadMask = [this, proxy](GrDeferredTextureUploadWritePixelsFn& writePixelsFn) {
        this->wait();  // 等待工作线程完成

        GrColorType pixelColorType = SkColorTypeToGrColorType(this->fPixels.info().colorType());

        // 如果工作线程分配失败，addr()为null，绘制使用未初始化纹理（但不崩溃）
        if (this->fPixels.addr()) {
            writePixelsFn(proxy,
                          SkIRect::MakeSize(fPixels.dimensions()),
                          pixelColorType,
                          this->fPixels.addr(),
                          this->fPixels.rowBytes());
        }

        // 上传完成，通知代理释放上传器
        proxy->texPriv().resetDeferredUploader();
    };

    flushState->addASAPUpload(std::move(uploadMask));
    fScheduledUpload = true;
}
```

**关键点：**
- `wait()` 阻塞直到工作线程发出信号
- 防护检查避免工作线程分配失败时崩溃
- 上传后自动清理上传器

### signalAndFreeData 实现

```cpp
void signalAndFreeData() {
    this->freeData();  // 调用虚函数释放载荷
    fPixelsReady.signal();  // 通知主线程
}
```

### wait 实现

```cpp
void wait() {
    if (!fWaited) {
        fPixelsReady.wait();  // 阻塞直到信号
        fWaited = true;
    }
}
```

使用标志避免重复等待。

### 模板类实现

```cpp
template <typename T>
class GrTDeferredProxyUploader : public GrDeferredProxyUploader {
public:
    template <typename... Args>
    GrTDeferredProxyUploader(Args&&... args)
        : fData(std::make_unique<T>(std::forward<Args>(args)...)) {
    }

    ~GrTDeferredProxyUploader() override {
        // 确保等待，避免在析构前工作线程仍在使用fData
        this->wait();
    }

    T& data() { return *fData; }

private:
    void freeData() override {
        fData.reset();  // 释放载荷数据
    }

    std::unique_ptr<T> fData;
};
```

**模板参数 T：**
- `SkPath`: 路径渲染
- 裁剪区域信息
- 其他需要传递给工作线程的数据

### 生命周期管理

```cpp
// 代理持有上传器
proxy->texPriv().setDeferredUploader(uploader);

// 上传完成后释放
proxy->texPriv().resetDeferredUploader();  // 上传器析构
```

**如果代理提前删除：**
```cpp
~GrTDeferredProxyUploader() {
    this->wait();  // 等待工作线程完成，避免悬挂指针
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkAutoPixmapStorage` | 像素数据存储 |
| `SkSemaphore` | 线程同步 |
| `GrOpFlushState` | 刷新状态，调度上传 |
| `GrTextureProxy` | 纹理代理 |
| `GrTextureProxyPriv` | 代理特权访问 |
| `GrDeferredTextureUploadWritePixelsFn` | 上传函数类型 |
| `GrColorType` | 颜色类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| 软件裁剪系统 | 生成裁剪遮罩纹理 |
| 软件路径渲染器 | 生成路径纹理 |
| `GrOp` 子类 | 创建上传器并关联代理 |
| `GrOpList` | 在刷新时调度上传 |

## 设计模式与设计决策

### 模板方法模式（Template Method Pattern）

基类定义流程，子类提供数据释放策略：
```cpp
class GrDeferredProxyUploader {
    void signalAndFreeData() {
        this->freeData();  // 虚函数
        fPixelsReady.signal();
    }
private:
    virtual void freeData() {}  // 可重写
};

template <typename T>
class GrTDeferredProxyUploader : public GrDeferredProxyUploader {
    void freeData() override {
        fData.reset();  // 释放类型T的数据
    }
};
```

### 生产者-消费者模式（Producer-Consumer Pattern）

使用信号量同步：
- **生产者（工作线程）**：生成像素，调用 `signalAndFreeData()`
- **消费者（主线程）**：等待像素，调用 `wait()`，上传到GPU

### RAII（Resource Acquisition Is Initialization）

使用智能指针和析构函数管理资源：
```cpp
~GrTDeferredProxyUploader() {
    this->wait();  // 确保资源释放前完成
}
```

### 完美转发（Perfect Forwarding）

模板构造函数支持任意载荷类型：
```cpp
template <typename... Args>
GrTDeferredProxyUploader(Args&&... args)
    : fData(std::make_unique<T>(std::forward<Args>(args)...)) {
}
```

### 设计决策

1. **延迟上传**：使用ASAP上传模式，在帧开始时批量上传
2. **信号量同步**：简单高效的线程同步机制
3. **模板载荷**：灵活支持不同类型的工作数据
4. **防护检查**：像素分配失败时不崩溃，仅绘制未初始化内容
5. **自动清理**：上传完成后自动释放上传器，防止内存泄漏

## 性能考量

### 多线程加速

CPU密集型操作（如路径光栅化）在工作线程中执行：
```cpp
taskGroup->add([uploader] {
    // 不阻塞主线程
    canvas.drawPath(uploader->data(), paint);
    uploader->signalAndFreeData();
});
```

**收益：**
- 主线程可以继续提交GPU命令
- 多个上传任务可以并行执行
- 减少帧延迟

### ASAP上传优化

使用 `addASAPUpload` 而非内联上传：
- 在帧开始时批量上传
- 减少GPU状态切换
- 提高上传效率

### 信号量开销

`SkSemaphore` 基于操作系统原语：
- 未准备就绪时阻塞，无忙等待
- 开销低于条件变量 + 互斥锁

### 避免重复上传

```cpp
if (fScheduledUpload) {
    return;  // 多个操作引用同一代理时避免重复
}
```

### 早期数据释放

工作线程完成后立即释放载荷：
```cpp
void signalAndFreeData() {
    this->freeData();  // 尽早释放内存
    fPixelsReady.signal();
}
```

### 防护检查开销

```cpp
if (this->fPixels.addr()) {
    writePixelsFn(...);  // 仅在分配成功时上传
}
```

轻量级检查，避免崩溃。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkAutoPixmapStorage.h` | 依赖 | 像素数据存储 |
| `include/private/base/SkSemaphore.h` | 依赖 | 信号量同步 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | 刷新状态 |
| `src/gpu/ganesh/GrTextureProxy.h` | 使用 | 纹理代理 |
| `src/gpu/ganesh/GrTextureProxyPriv.h` | 使用 | 代理特权访问 |
| `src/gpu/ganesh/GrDeferredUpload.h` | 依赖 | 延迟上传函数类型 |
| `src/gpu/ganesh/ops/SoftwarePathRenderer.cpp` | 被使用 | 软件路径渲染器 |
| 软件裁剪系统 | 被使用 | 裁剪遮罩生成 |
