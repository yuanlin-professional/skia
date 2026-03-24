# src/capture - 绘制操作捕获与录制模块

## 概述

`src/capture` 目录是 Skia 图形库中用于捕获和录制绘制操作的模块。该模块于 2025 年新增（代码版权标注 2025 Google LLC），目前仍处于积极开发阶段（版本号为 0，表示 API 尚不稳定）。其核心目标是将 `SkCanvas` 上的所有绘制操作记录为 `SkPicture` 对象，并支持将这些录制序列化为二进制数据以及从数据反序列化恢复。

该模块的设计围绕三个核心类展开：`SkCaptureManager` 作为捕获会话的管理器，控制捕获的启动和停止；`SkCaptureCanvas` 作为透明代理画布，在不影响正常绘制的前提下同时将操作录制到 `SkPictureRecorder`；`SkCapture` 作为捕获结果的容器，负责 `SkPicture` 集合的序列化和反序列化。

`SkCaptureCanvas` 继承自 `SkNWayCanvas`（N-Way 广播画布），能够将每个绘制调用同时转发到多个目标画布。在捕获模式下，它持有基础画布和录制画布两个目标；在非捕获模式下，仅持有基础画布。这种设计使得捕获操作对上层调用方完全透明。

该模块的设计目标之一是支持客户端图形调试和性能分析。通过捕获绘制操作序列，开发者可以回放和检查图形输出的每一步，这对于诊断渲染问题和优化绘制性能非常有价值。目前的实现还包含多个 TODO 注释，指示未来将增加的功能，如 Surface 内容 ID 追踪、多 Surface 支持和线程安全等。

## 架构图

```
+------------------------------------------------------------------+
|                    客户端应用层                                    |
|              (使用 SkCanvas 进行绘制)                             |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                   SkCaptureManager                                |
|   (捕获会话管理器，控制开始/停止/快照)                            |
|                                                                   |
|   toggleCapture(bool)  -- 开启/关闭捕获                          |
|   makeCaptureCanvas()  -- 创建捕获画布                            |
|   snapPictures()       -- 对所有追踪的画布做快照                  |
|   snapPicture(surface) -- 对特定 Surface 做快照                   |
|   getLastCapture()     -- 获取最后的捕获结果                      |
+------------------------------------------------------------------+
        |                                    |
        v                                    v
+------------------+              +---------------------+
| SkCaptureCanvas  |              | SkCapture           |
| (N-Way 代理画布) |              | (捕获数据容器)      |
|                  |              |                     |
| 基础画布 + 录制  |              | 序列化/反序列化     |
| 画布的广播       |              | SkPicture 集合管理  |
|                  |              |                     |
| pollCapturing    |              | MakeFromData()      |
|   Status()       |              | MakeFromPictures()  |
| snapPicture()    |              | serializeCapture()  |
| attachRecording  |              | getPicture(i)       |
|   Canvas()       |              +---------------------+
| detachRecording  |
|   Canvas()       |
+--------+---------+
         |
         v
+------------------+
| SkNWayCanvas     |
| (N-Way 基类)     |
+------------------+
    |           |
    v           v
+--------+ +------------------+
| 基础   | | SkPicture-       |
| 画布   | |   Recorder       |
| (实际  | | (录制画布)        |
|  渲染) | |                  |
+--------+ +------------------+
```

## 目录结构

```
src/capture/
  BUILD.bazel              -- Bazel 构建配置
  SkCapture.h              -- SkCapture 类声明（捕获数据容器）
  SkCapture.cpp            -- SkCapture 类实现（序列化/反序列化）
  SkCaptureCanvas.h        -- SkCaptureCanvas 类声明（捕获代理画布）
  SkCaptureCanvas.cpp      -- SkCaptureCanvas 类实现（绘制操作转发与录制）
  SkCaptureManager.h       -- SkCaptureManager 类声明（捕获会话管理器）
  SkCaptureManager.cpp     -- SkCaptureManager 类实现
```

## 关键类与函数

### SkCaptureManager（捕获会话管理器）
- **位置**: `src/capture/SkCaptureManager.h`, `src/capture/SkCaptureManager.cpp`
- **继承**: `SkRefCnt`（引用计数）
- **职责**: 管理捕获会话的生命周期，协调多个 SkCaptureCanvas

#### 核心方法
- `makeCaptureCanvas(SkCanvas*)` -- 创建一个包装指定画布的 SkCaptureCanvas
  - 将新创建的 SkCaptureCanvas 加入 `fTrackedCanvases` 追踪列表
  - 返回裸指针供调用方使用

- `toggleCapture(bool capturing)` -- 切换捕获状态
  - 当从捕获状态切换到非捕获状态时：
    1. 对所有追踪的画布执行快照（`snapPictures()`）
    2. 将收集的 `SkPicture` 打包为 `SkCapture` 对象（`fLastCapture`）
    3. 清空 Picture 列表

- `snapPictures()` -- 对所有追踪的画布执行快照
  - 遍历 `fTrackedCanvases`，对每个画布调用 `snapPicture()`

- `snapPicture(SkSurface*)` -- 对特定 Surface 关联的画布执行快照
  - 通过 `canvas->getSurface() == surface` 匹配画布

- `getLastCapture()` -- 获取最后一次捕获会话的结果

- `isCurrentlyCapturing()` -- 查询当前是否正在捕获（使用 `std::atomic<bool>`）

#### 核心成员
- `fIsCurrentlyCapturing` -- 原子布尔值，捕获状态标志
- `fTrackedCanvases` -- 所有被管理的 SkCaptureCanvas 列表
- `fPictures` -- 当前捕获会话中收集的 SkPicture 列表
- `fLastCapture` -- 最后一次完成的捕获结果

### SkCaptureCanvas（捕获代理画布）
- **位置**: `src/capture/SkCaptureCanvas.h`, `src/capture/SkCaptureCanvas.cpp`
- **继承**: `SkNWayCanvas`
- **职责**: 作为透明代理，将绘制操作同时转发到基础画布和录制画布

#### 核心方法
- `snapPicture()` -- 生成当前录制的 SkPicture
  1. 移除过期的录制画布（`detachRecordingCanvas()`）
  2. 完成 `SkPictureRecorder` 的录制（`finishRecordingAsPicture()`）
  3. 重新开始一次新的录制（`attachRecordingCanvas()`）
  4. 返回 SkPicture

- `pollCapturingStatus()` -- 轮询捕获状态
  - 检查 `SkCaptureManager::isCurrentlyCapturing()`
  - 状态变化时动态附加或分离录制画布

- `attachRecordingCanvas()` -- 附加录制画布
  - 通过 `fRecorder.beginRecording()` 创建录制画布
  - 将录制画布添加到 NWayCanvas 的目标列表

- `detachRecordingCanvas()` -- 分离录制画布
  - 从 NWayCanvas 的目标列表中移除录制画布

#### 重写的绘制方法
所有绘制方法（`onDrawPaint`, `onDrawRect`, `onDrawPath`, `onDrawImage2` 等）以及状态方法（`willSave`, `willRestore`, `didConcat44`, `onClipRect` 等）都遵循相同的模式：
1. 调用 `pollCapturingStatus()` -- 检查并更新捕获状态
2. 调用父类 `SkNWayCanvas` 对应方法 -- 广播到所有目标画布

#### 隐藏的方法
`addCanvas()`, `removeCanvas()`, `removeAll()` 被重写为私有方法，防止外部直接操作画布列表。

### SkCapture（捕获数据容器）
- **位置**: `src/capture/SkCapture.h`, `src/capture/SkCapture.cpp`
- **继承**: `SkRefCnt`
- **职责**: 封装捕获结果（SkPicture 集合），提供序列化和反序列化功能

#### 数据格式
```
+--------+--------+---------+--------------+
| magic1 | magic2 | version | pictureCount |
| "skia" | "capt" | uint32  | uint32       |
+--------+--------+---------+--------------+
| pictureDataSize_0 | pictureData_0 |
| pictureDataSize_1 | pictureData_1 |
| ...                                |
+------------------------------------+
```

#### 工厂方法
- `MakeFromData(sk_sp<const SkData>)` -- 从二进制数据反序列化
  1. 验证魔数（"skia" + "capt"）
  2. 验证版本号
  3. 读取 Picture 数量
  4. 逐个反序列化 SkPicture

- `MakeFromPictures(TArray<sk_sp<SkPicture>>)` -- 从 SkPicture 数组创建

#### 核心方法
- `serializeCapture()` -- 将捕获序列化为 SkData
  - 写入魔数 + 版本 + Picture 数量
  - 逐个序列化 SkPicture（附带自定义图像序列化 proc）

- `getPicture(int i)` -- 按索引获取 SkPicture

- `getMetadata()` -- 获取元数据（版本号、Picture 数量）

#### 图像序列化回调
- `serializeImageProc()` -- 图像序列化处理（当前返回占位符 contentID = -1）
- `deserializeImageProc()` -- 图像反序列化处理（当前返回品红色 5x5 占位图像）
- **TODO**: 未来将实现基于 Surface contentID 的图像引用追踪

#### 常量
- `kMagic1` = `SkSetFourByteTag('s','k','i','a')` -- 文件魔数第一部分
- `kMagic2` = `SkSetFourByteTag('c','a','p','t')` -- 文件魔数第二部分
- `kVersion` = 0 -- 当前版本号（不稳定）

### Metadata 结构体
- **位置**: `src/capture/SkCapture.h`
- **字段**: `version` (uint32), `numPictures` (uint32)

## 依赖关系

### 内部依赖
- `include/core` -- `SkCanvas`, `SkPicture`, `SkPictureRecorder`, `SkData`, `SkImage`, `SkBitmap`, `SkSurface`, `SkRefCnt`, `SkStream`, `SkSerialProcs`
- `include/utils` -- `SkNWayCanvas`（N-Way 广播画布基类）
- `src/core` -- `SkCanvasPriv`

### 被依赖
- 客户端调试工具
- 图形调试器

## 设计模式分析

### 代理模式（Proxy）
`SkCaptureCanvas` 作为 `SkCanvas` 的透明代理，在不改变原有绘制行为的前提下增加了录制功能。通过继承 `SkNWayCanvas`，绘制操作被自动广播到基础画布（实际渲染）和录制画布（捕获记录）。

### 观察者模式（Observer）
`pollCapturingStatus()` 机制实现了一种轮询式的观察者模式。每个绘制操作前都会检查 `SkCaptureManager` 的捕获状态，动态地附加或分离录制画布。使用 `std::atomic<bool>` 确保了状态查询的线程安全性。

### 命令模式（Command）
`SkPicture` 本质上是绘制命令的序列化表示。通过 `SkPictureRecorder` 将绘制操作录制为命令序列，后续可以回放这些命令。

### 快照模式（Memento）
`snapPicture()` 方法在不中断绘制流程的情况下获取当前录制的快照。它通过结束当前录制、保存 SkPicture、然后立即开始新的录制来实现连续捕获。

### 序列化模式（Serialization）
`SkCapture` 类实现了自定义二进制序列化格式，包含魔数验证、版本控制和图片数据的分块存储，支持 SkPicture 集合的持久化和恢复。

## 数据流

### 捕获生命周期
```
1. 初始化阶段:
   SkCaptureManager manager;
   SkCanvas* captureCanvas = manager.makeCaptureCanvas(baseCanvas);
       |
       v
   SkCaptureCanvas 创建，包装 baseCanvas
   fList = [baseCanvas]  (仅一个目标)

2. 开始捕获:
   manager.toggleCapture(true);
   fIsCurrentlyCapturing = true
       |
       v
   下一次绘制调用触发 pollCapturingStatus():
   attachRecordingCanvas() --> fRecorder.beginRecording()
   fList = [baseCanvas, recordingCanvas]  (两个目标)

3. 绘制阶段 (每次绘制调用):
   captureCanvas->drawRect(...)
       |
       +---> pollCapturingStatus() -- 确认仍在捕获
       |
       +---> SkNWayCanvas::onDrawRect()
               |
               +---> baseCanvas->drawRect()      -- 实际渲染
               +---> recordingCanvas->drawRect()  -- 录制操作

4. 中间快照 (可选):
   manager.snapPicture(surface);
       |
       v
   canvas->snapPicture():
     detachRecordingCanvas()
     fRecorder.finishRecordingAsPicture() --> sk_sp<SkPicture>
     attachRecordingCanvas() -- 开始新的录制

5. 停止捕获:
   manager.toggleCapture(false);
       |
       v
   snapPictures() -- 对所有画布快照
   SkCapture::MakeFromPictures(fPictures) --> fLastCapture
   fPictures.clear()
   fIsCurrentlyCapturing = false
       |
       v
   下一次绘制调用触发 pollCapturingStatus():
   detachRecordingCanvas()
   fList = [baseCanvas]  (恢复为一个目标)

6. 获取结果:
   sk_sp<SkCapture> capture = manager.getLastCapture();
   sk_sp<SkData> data = capture->serializeCapture();
       |
       v
   二进制数据: [magic1][magic2][version][count][size0][picture0][size1][picture1]...
```

### 序列化/反序列化流程
```
序列化:
  SkCapture::serializeCapture()
    |
    +---> 写入魔数 "skia" + "capt"
    +---> 写入版本号 (0)
    +---> 写入 Picture 数量
    +---> 对每个 SkPicture:
    |       +---> picture->serialize(procs) -- 含自定义图像 proc
    |       +---> 写入数据大小
    |       +---> 写入 Picture 数据
    |
    v
  sk_sp<SkData> -- 可写入文件或网络传输

反序列化:
  SkCapture::MakeFromData(data)
    |
    +---> 验证魔数
    +---> 验证版本号
    +---> 读取 Picture 数量
    +---> 对每个 Picture:
    |       +---> 读取数据大小
    |       +---> 读取 Picture 数据
    |       +---> SkPicture::MakeFromData(procs) -- 含自定义图像 proc
    |
    v
  sk_sp<SkCapture> -- 可遍历和回放 SkPicture
```

## 相关文档与参考

- **SkPicture**: `include/core/SkPicture.h` -- Skia 绘制记录和回放机制
- **SkPictureRecorder**: `include/core/SkPictureRecorder.h` -- SkPicture 录制器
- **SkNWayCanvas**: `include/utils/SkNWayCanvas.h` -- N-Way 广播画布基类
- **SkSerialProcs**: `include/core/SkSerialProcs.h` -- 自定义序列化回调
- **Bug Tracker**: b/412351769 -- 相关开发跟踪 Issue
- **版本说明**: 当前版本号为 0，API 处于不稳定状态，后续版本可能会有重大变更
