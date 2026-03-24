# SkCaptureManager

> 源文件: src/capture/SkCaptureManager.h, src/capture/SkCaptureManager.cpp

## 概述

`SkCaptureManager` 是 Skia 捕获系统的管理器类，负责协调多个画布的捕获会话。它维护所有被跟踪的 `SkCaptureCanvas` 实例，控制捕获的启动和停止，并将捕获的图片组织成 `SkCapture` 对象。

该类继承自 `SkRefCnt`，支持智能指针管理。作为捕获系统的中央协调者，它提供了统一的接口来管理多个并发的画布捕获操作，并确保捕获数据的正确收集和存储。

## 架构位置

`SkCaptureManager` 在 Skia 捕获架构中处于管理层：

- **上层接口**: 被应用代码调用以启动、停止和查询捕获会话
- **管理对象**: 创建和管理多个 `SkCaptureCanvas` 实例
- **数据聚合**: 将所有捕获的 `SkPicture` 组织成 `SkCapture` 对象
- **生命周期控制**: 通过引用计数管理资源，确保画布和图片的正确清理

典型使用流程：
1. 应用创建 `SkCaptureManager` 实例
2. 调用 `makeCaptureCanvas` 包装需要捕获的画布
3. 调用 `toggleCapture(true)` 开始记录
4. 正常绘图操作
5. 调用 `toggleCapture(false)` 停止并生成捕获数据
6. 使用 `getLastCapture()` 获取捕获结果

## 主要类与结构体

### SkCaptureManager 类

**继承关系**: 继承自 `SkRefCnt`，支持 `sk_sp<SkCaptureManager>` 智能指针管理。

**主要成员变量**:
- `std::atomic<bool> fIsCurrentlyCapturing`: 原子布尔值，标识当前是否正在捕获
- `skia_private::TArray<std::unique_ptr<SkCaptureCanvas>> fTrackedCanvases`: 被跟踪的所有捕获画布
- `skia_private::TArray<sk_sp<SkPicture>> fPictures`: 累积的图片集合
- `sk_sp<SkCapture> fLastCapture`: 最近一次完成的捕获对象

**设计特点**:
- 使用 `std::unique_ptr` 管理画布生命周期，确保独占所有权
- 使用 `sk_sp` 管理图片和捕获对象，支持共享所有权
- 使用 `std::atomic` 提供基本的线程安全性（部分实现）

## 公共 API 函数

### 构造函数
```cpp
SkCaptureManager()
```
默认构造函数，初始化空的管理器。所有成员变量使用默认初始化（`fIsCurrentlyCapturing = false`）。

### 画布管理

**makeCaptureCanvas**
```cpp
SkCanvas* makeCaptureCanvas(SkCanvas* canvas)
```
创建并注册一个新的捕获画布：
1. 创建 `SkCaptureCanvas` 包装原始画布
2. 使用 `std::make_unique` 分配并管理生命周期
3. 将画布添加到 `fTrackedCanvases` 进行跟踪
4. 返回裸指针供调用者使用

**注意**: 返回的指针由 `SkCaptureManager` 拥有，调用者不应 `delete`。

### 捕获控制

**toggleCapture**
```cpp
void toggleCapture(bool capturing)
```
切换捕获状态：
- 从 `true` 到 `false`（停止捕获）时：
  1. 调用 `snapPictures()` 收集所有画布的图片
  2. 创建 `SkCapture` 对象并保存到 `fLastCapture`
  3. 清空 `fPictures` 准备下一次捕获
- 从 `false` 到 `true`（开始捕获）时：
  - 仅更新状态标志

**线程安全问题**: 代码注释提到需要使用 `exchange()` 和互斥锁改进线程安全性。

**isCurrentlyCapturing**
```cpp
bool isCurrentlyCapturing() const
```
查询当前是否正在捕获。由于使用 `std::atomic`，该操作是线程安全的。

### 图片收集

**snapPictures**
```cpp
void snapPictures()
```
遍历所有跟踪的画布，调用其 `snapPicture()` 方法获取图片并添加到 `fPictures`。空指针和空图片会被忽略。

**snapPicture**
```cpp
void snapPicture(SkSurface* surface)
```
捕获特定 Surface 关联画布的图片：
1. 遍历所有跟踪的画布
2. 通过 `canvas->getSurface()` 匹配目标 Surface
3. 捕获该画布的图片并添加到 `fPictures`
4. 找到后立即返回

**待实现**: 为每个图片分配 `contentID` 并跟踪其所属 Surface。

### 结果访问

**getLastCapture**
```cpp
sk_sp<SkCapture> getLastCapture() const
```
返回最近一次完成的捕获对象。如果尚未完成捕获，返回空指针。

## 内部实现细节

### 画布生命周期管理

使用 `std::unique_ptr<SkCaptureCanvas>` 存储画布确保：
- 自动清理：管理器销毁时所有画布自动析构
- 独占所有权：画布不会被意外复制或共享
- 移动语义：支持高效的所有权转移（`std::move`）

`makeCaptureCanvas` 的实现模式：
```cpp
auto newCanvas = std::make_unique<SkCaptureCanvas>(canvas, this);
auto rawCanvasPtr = newCanvas.get();
fTrackedCanvases.emplace_back(std::move(newCanvas));
return rawCanvasPtr;
```
先获取裸指针，再移动所有权到容器，避免悬空指针。

### 图片收集策略

**批量收集** (`snapPictures`):
- 遍历所有画布，不关心 Surface 归属
- 用于停止捕获时一次性收集所有内容
- 简单但缺乏组织结构

**按 Surface 收集** (`snapPicture`):
- 通过 Surface 指针精确匹配画布
- 用于中途快照特定 Surface 的内容
- 支持更细粒度的控制

### 捕获会话生命周期

完整的捕获会话流程：
1. **开始**: `toggleCapture(true)` → 设置 `fIsCurrentlyCapturing = true`
2. **记录**: 应用绘图 → `SkCaptureCanvas` 拦截命令 → 记录到内部 `SkPictureRecorder`
3. **快照**: 可选调用 `snapPicture(surface)` 进行中途捕获
4. **结束**: `toggleCapture(false)` → 调用 `snapPictures()` → 创建 `SkCapture` → 清空 `fPictures`
5. **访问**: `getLastCapture()` 获取结果

### 原子操作

`fIsCurrentlyCapturing` 使用 `std::atomic<bool>` 提供：
- **无锁读取**: `isCurrentlyCapturing()` 可被任意线程安全调用
- **基本写安全**: 赋值操作原子化
- **不足**: `toggleCapture` 中的读-改-写序列不是原子的（`if (capturing != fIsCurrentlyCapturing)`）

## 依赖关系

### 直接依赖
- **SkCaptureCanvas**: 创建和管理捕获画布
- **SkCapture**: 使用其工厂方法创建捕获对象
- **SkPicture**: 存储从画布捕获的图片
- **SkCanvas**: 作为包装对象的参数类型
- **SkSurface**: 用于识别和匹配画布

### 标准库依赖
- **std::atomic**: 提供线程安全的布尔标志
- **std::unique_ptr**: 管理画布的独占所有权
- **skia_private::TArray**: Skia 自定义的动态数组

### 被依赖
- **应用代码**: 直接使用管理器进行捕获控制
- **SkCaptureCanvas**: 通过构造函数接收管理器指针（双向依赖）

## 设计模式与设计决策

### 管理器模式（Manager Pattern）
集中管理多个相关对象的生命周期和协调：
- **优势**: 统一入口，简化客户端代码
- **责任**: 创建、跟踪、协调和清理所有捕获画布
- **扩展性**: 易于添加全局捕获策略（如自动快照、内存限制）

### 观察者模式的简化实现
管理器跟踪多个画布，但不使用显式的观察者接口：
- 画布不主动通知管理器
- 管理器主动拉取（pull）画布状态（调用 `snapPicture()`）
- 简化设计但牺牲了实时性

### 资源管理策略

**画布所有权**: `std::unique_ptr` 确保独占所有权
```cpp
skia_private::TArray<std::unique_ptr<SkCaptureCanvas>> fTrackedCanvases;
```

**图片共享**: `sk_sp` 允许捕获对象和管理器共享图片
```cpp
skia_private::TArray<sk_sp<SkPicture>> fPictures;
```

**捕获结果**: 使用 `sk_sp` 允许调用者保留捕获对象
```cpp
sk_sp<SkCapture> fLastCapture;
```

### 状态机设计

捕获状态转换：
```
[未捕获] --toggleCapture(true)--> [正在捕获]
[正在捕获] --toggleCapture(false)--> [未捕获] (触发 snapPictures 和创建 SkCapture)
```

状态查询通过 `isCurrentlyCapturing()` 实现，但实际捕获逻辑在 `SkCaptureCanvas` 中。

### 待改进的设计

1. **线程安全性不足**: `toggleCapture` 的检查和修改不是原子的
2. **缺少组织结构**: 图片平铺存储，缺少 Surface 和 ContentID 关联
3. **生命周期混乱**: 返回裸指针但由管理器拥有，容易误用
4. **内存管理**: 没有限制 `fPictures` 的大小，可能导致内存过度使用

## 性能考量

### 内存效率
- **优势**: 使用 `TArray` 而非 `std::vector`，针对 Skia 对象优化
- **风险**: `fPictures` 无上限，长时间捕获可能消耗大量内存
- **改进**: 考虑添加内存上限或自动分段捕获

### 并发性能
- **读取**: `isCurrentlyCapturing()` 的原子读取无锁，性能良好
- **写入**: `toggleCapture()` 未加锁，存在数据竞争风险
- **改进**: 使用 `std::mutex` 保护状态切换和图片收集

### 画布查找效率
`snapPicture(SkSurface*)` 使用线性搜索：
- **时间复杂度**: O(n)，n 为跟踪的画布数量
- **适用场景**: 画布数量较少时（< 100）性能可接受
- **改进**: 使用 `std::unordered_map<SkSurface*, SkCaptureCanvas*>` 提升到 O(1)

### 批量操作
`snapPictures()` 一次性处理所有画布：
- **优势**: 减少函数调用开销
- **劣势**: 阻塞时间较长，不适合实时系统
- **改进**: 考虑增量快照或异步处理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/capture/SkCaptureCanvas.h` | 依赖 | 被管理的捕获画布类 |
| `src/capture/SkCapture.h` | 依赖 | 捕获数据的容器类 |
| `include/core/SkPicture.h` | 依赖 | 存储捕获的绘图命令 |
| `include/core/SkCanvas.h` | 依赖 | 基础画布接口 |
| `include/core/SkSurface.h` | 依赖 | 用于识别画布所属表面 |
| `include/core/SkRefCnt.h` | 依赖 | 引用计数基类 |
| `include/private/base/SkTArray.h` | 依赖 | 动态数组容器 |
