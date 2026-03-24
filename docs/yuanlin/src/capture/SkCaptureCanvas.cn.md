# SkCaptureCanvas

> 源文件: src/capture/SkCaptureCanvas.h, src/capture/SkCaptureCanvas.cpp

## 概述

`SkCaptureCanvas` 是 Skia 捕获系统中的核心拦截器类，继承自 `SkNWayCanvas`。它包装一个基础画布（base canvas），并在捕获模式下同时将绘图命令转发到基础画布和记录画布（recording canvas）。这种双路转发机制使得应用可以在不中断正常渲染的同时记录所有绘图操作。

该类管理 `SkPictureRecorder` 的生命周期，根据 `SkCaptureManager` 的状态动态地启动和停止记录。当捕获处于活动状态时，所有绘图操作都会被记录到 `SkPicture` 对象中，随后可以序列化、分析或重放。

## 架构位置

`SkCaptureCanvas` 在 Skia 捕获架构中处于拦截层：

- **继承关系**: 继承自 `SkNWayCanvas`（多路画布），后者继承自 `SkCanvas`
- **管理者**: 由 `SkCaptureManager` 创建和管理生命周期
- **包装对象**: 包装应用的原始 `SkCanvas`，透明地拦截所有绘图调用
- **记录器**: 使用 `SkPictureRecorder` 将命令记录为 `SkPicture`

数据流向：
```
应用调用 → SkCaptureCanvas → SkNWayCanvas → [基础画布, 记录画布]
                                                    ↓            ↓
                                              实际渲染      SkPicture
```

## 主要类与结构体

### SkCaptureCanvas 类

**继承关系**:
```
SkCaptureCanvas → SkNWayCanvas → SkCanvas → SkRefCnt
```

**主要成员变量**:
- `bool fCapturing`: 本地捕获状态缓存（避免频繁查询管理器）
- `SkPictureRecorder fRecorder`: 图片记录器，管理记录画布的生命周期
- `SkCanvas* fBaseCanvas`: 原始画布的裸指针（由外部拥有）
- `SkCaptureManager* fManager`: 管理器指针，用于查询全局捕获状态

**设计特点**:
- 使用裸指针而非智能指针（生命周期由外部管理）
- 继承 `SkNWayCanvas` 自动实现多路转发
- 重写所有虚函数以插入状态轮询逻辑

## 公共 API 函数

### 构造与析构

**构造函数**
```cpp
SkCaptureCanvas(SkCanvas* canvas, SkCaptureManager* manager)
```
初始化捕获画布：
1. 调用 `SkNWayCanvas` 基类构造函数，传递画布尺寸
2. 保存基础画布和管理器指针
3. 将基础画布添加到多路转发列表（确保命令始终转发到原始画布）

**注意**: 传入的指针必须在 `SkCaptureCanvas` 生命周期内保持有效。

**析构函数**
```cpp
~SkCaptureCanvas() override
```
使用默认实现。`SkPictureRecorder` 会自动清理，不需要手动处理。

### 核心功能

**snapPicture**
```cpp
sk_sp<SkPicture> snapPicture()
```
捕获当前记录的绘图命令并生成 `SkPicture`：
1. 检查是否正在捕获，未捕获返回 `nullptr`
2. 分离记录画布（从多路列表移除）
3. 调用 `fRecorder.finishRecordingAsPicture()` 完成记录并获取图片
4. 重新附加新的记录画布（为后续捕获准备）

该方法允许中途获取快照而不停止捕获。

## 重写的虚函数

### 状态管理函数
- `willSave()`: 保存画布状态前调用
- `getSaveLayerStrategy()`: 确定保存图层的策略
- `onDoSaveBehind()`: 保存背后内容时调用
- `willRestore()`: 恢复画布状态前调用

### 变换函数
- `didConcat44(const SkM44&)`: 连接 4x4 矩阵
- `didSetM44(const SkM44&)`: 设置 4x4 矩阵
- `didScale(SkScalar, SkScalar)`: 缩放变换
- `didTranslate(SkScalar, SkScalar)`: 平移变换

### 裁剪函数
- `onClipRect()`: 矩形裁剪
- `onClipRRect()`: 圆角矩形裁剪
- `onClipPath()`: 路径裁剪
- `onClipShader()`: 着色器裁剪
- `onClipRegion()`: 区域裁剪
- `onResetClip()`: 重置裁剪区域

### 绘图函数（部分列举）
- `onDrawPaint()`: 绘制填充整个画布
- `onDrawPoints()`: 绘制点集
- `onDrawRect()`: 绘制矩形
- `onDrawOval()`: 绘制椭圆
- `onDrawPath()`: 绘制路径
- `onDrawImage2()`: 绘制图片
- `onDrawTextBlob()`: 绘制文本块
- `onDrawPicture()`: 绘制图片对象
- `onDrawVerticesObject()`: 绘制顶点数据
- `onDrawShadowRec()`: 绘制阴影

**共同模式**: 所有重写函数都遵循相同的模式：
```cpp
void SkCaptureCanvas::onDrawXXX(...) {
    this->pollCapturingStatus();
    this->SkNWayCanvas::onDrawXXX(...);
}
```

## 内部实现细节

### 状态轮询机制

**pollCapturingStatus**
```cpp
void pollCapturingStatus()
```
在每个绘图操作前调用，同步本地捕获状态与管理器全局状态：
1. 从管理器获取当前捕获状态 `shouldPoll = fManager->isCurrentlyCapturing()`
2. 比较本地状态 `fCapturing` 与全局状态
3. 状态改变时：
   - 开始捕获: 调用 `attachRecordingCanvas()`
   - 停止捕获: 调用 `detachRecordingCanvas()`
4. 更新本地状态 `fCapturing = shouldPoll`

**设计目的**: 避免在管理器中直接操作画布，保持松耦合。

### 记录画布管理

**attachRecordingCanvas**
```cpp
void attachRecordingCanvas()
```
启动记录并将记录画布添加到多路列表：
1. 断言当前只有基础画布（`fList.size() == 1`）
2. 调用 `fRecorder.beginRecording()` 创建新的记录画布
3. 使用 `addCanvas()` 将记录画布添加到多路转发列表

添加后，`SkNWayCanvas` 会自动将所有命令转发到基础画布和记录画布。

**detachRecordingCanvas**
```cpp
void detachRecordingCanvas()
```
从多路列表移除记录画布：
1. 断言当前有两个画布（`fList.size() == 2`）
2. 调用 `removeCanvas(fRecorder.getRecordingCanvas())` 移除记录画布

移除后，命令仅转发到基础画布，记录停止。

**生命周期管理**:
- `SkPictureRecorder` 持有记录画布的所有权
- `finishRecordingAsPicture()` 会销毁旧的记录画布
- 必须先分离画布再完成记录，避免悬空指针

### 多路转发原理

`SkNWayCanvas` 维护画布列表 `fList`，其 `onDrawXXX` 方法会遍历列表：
```cpp
for (SkCanvas* canvas : fList) {
    canvas->drawXXX(...);
}
```

`SkCaptureCanvas` 利用这一机制：
- 始终包含基础画布（索引 0）
- 捕获时添加记录画布（索引 1）
- 所有命令自动转发到两个目标

### 表面删除处理

**onSurfaceDelete**
```cpp
void onSurfaceDelete() override
```
当关联的 Surface 被删除时调用（Skia 内部回调）。当前实现为空，TODO 注释表明未来需要通知管理器进行清理。

### 隐藏的 NWay 管理函数

通过 `private` 继承隐藏 `SkNWayCanvas` 的画布管理接口：
```cpp
void addCanvas(SkCanvas* canvas) override {SkNWayCanvas::addCanvas(canvas);}
void removeCanvas(SkCanvas* canvas) override {SkNWayCanvas::removeCanvas(canvas);}
void removeAll() override {SkNWayCanvas::removeAll();}
```

**目的**: 防止外部代码直接操作画布列表，确保状态一致性。

## 依赖关系

### 直接依赖
- **SkNWayCanvas**: 基类，提供多路转发功能
- **SkPictureRecorder**: 记录绘图命令为 `SkPicture`
- **SkCaptureManager**: 提供全局捕获状态
- **SkCanvas**: 基础画布类型
- **SkPicture**: 记录结果的类型

### 间接依赖（通过重写的函数）
- **SkPaint**: 绘图样式参数
- **SkPath**: 路径数据
- **SkImage**: 图片对象
- **SkTextBlob**: 文本块
- **SkVertices**: 顶点数据
- **SkShader**: 着色器
- **SkM44**: 4x4 矩阵

### 被依赖
- **SkCaptureManager**: 创建和管理 `SkCaptureCanvas` 实例
- **应用代码**: 间接使用（通过 `SkCanvas*` 接口）

## 设计模式与设计决策

### 代理模式（Proxy Pattern）
`SkCaptureCanvas` 作为基础画布的代理：
- **透明性**: 实现相同的 `SkCanvas` 接口
- **拦截**: 在转发前插入捕获逻辑
- **扩展**: 不修改基础画布的行为

### 装饰器模式（Decorator Pattern）
动态添加记录功能而不改变原始画布：
- **包装**: 通过组合而非继承扩展功能
- **可选**: 捕获可动态启用/禁用
- **叠加**: 可以在多个层次包装画布

### 观察者模式（简化版）
通过轮询实现状态同步：
- **优势**: 简单实现，无需注册/注销机制
- **劣势**: 每次绘图调用都轮询，有性能开销
- **改进**: 考虑使用事件通知机制

### 生命周期管理策略

**裸指针的使用**:
- `fBaseCanvas` 和 `fManager` 使用裸指针
- 假设外部保证生命周期（由 `SkCaptureManager` 管理）
- 避免循环引用和复杂的所有权问题

**记录画布的临时性**:
- 每次 `snapPicture()` 都创建新的记录画布
- 旧画布在 `finishRecordingAsPicture()` 后自动销毁
- 避免状态污染

### 状态一致性保证

**断言检查**:
```cpp
SkASSERT(this->fList.size() == 1);  // attachRecordingCanvas
SkASSERT(this->fList.size() == 2);  // detachRecordingCanvas
```
调试模式下验证画布列表状态，捕获编程错误。

**本地缓存**:
`fCapturing` 缓存避免重复查询管理器，同时通过 `pollCapturingStatus` 保持同步。

## 性能考量

### 轮询开销
每个绘图操作都调用 `pollCapturingStatus()`：
- **成本**: 一次管理器函数调用 + 一次布尔比较
- **优化**: `isCurrentlyCapturing()` 使用 `std::atomic`，无锁读取
- **影响**: 对于大量小绘图操作（如文本），累积开销可能显著
- **改进**: 考虑批量轮询或事件驱动模型

### 多路转发开销
`SkNWayCanvas` 每次调用都遍历画布列表：
- **成本**: 两次函数调用（基础画布 + 记录画布）
- **优化**: 仅两个画布，遍历开销可忽略
- **瓶颈**: 记录画布的写入（序列化命令）比实际渲染慢

### 内存使用
- **SkPictureRecorder**: 内部缓冲绘图命令，内存随命令数增长
- **风险**: 长时间不调用 `snapPicture()` 可能导致内存占用过高
- **缓解**: 应定期快照或限制记录时长

### 记录画布的性能
`SkPicture` 记录是纯 CPU 操作：
- 无 GPU 加速
- 需要序列化所有参数（路径、图片、文本等）
- 对于复杂场景可能成为瓶颈

### 虚函数调用开销
重写所有虚函数带来额外间接调用：
- **成本**: 每次调用多一层虚函数表查找
- **优化**: 现代 CPU 的分支预测减轻影响
- **不可避免**: 继承 `SkCanvas` 必然引入虚函数

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/utils/SkNWayCanvas.h` | 基类 | 多路画布转发基础设施 |
| `src/capture/SkCaptureManager.h` | 管理者 | 创建和控制捕获会话 |
| `include/core/SkPictureRecorder.h` | 依赖 | 记录绘图命令为 SkPicture |
| `include/core/SkPicture.h` | 依赖 | 记录结果的容器 |
| `include/core/SkCanvas.h` | 基类 | 画布基础接口 |
| `src/core/SkCanvasPriv.h` | 依赖 | 画布内部工具函数 |
| `include/core/SkRefCnt.h` | 基类 | 引用计数基类 |
| `include/private/base/SkAssert.h` | 工具 | 调试断言宏 |
