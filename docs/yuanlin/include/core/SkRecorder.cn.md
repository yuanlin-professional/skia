# SkRecorder

> 源文件: `include/core/SkRecorder.h`

## 概述
SkRecorder 是 Skia 绘图命令记录系统的抽象基类，定义了统一的接口来记录、捕获和回放绘图操作。它支持多种后端（CPU、Ganesh GPU、Graphite GPU），并提供了绘图命令捕获的调试功能。

## 架构位置
位于 Skia 核心模块 (`include/core`)，作为绘图系统的基础抽象层。它连接了上层的 SkCanvas 和底层的各种渲染后端，是 Skia 渲染管线中的关键组件。

## 主要类与结构体

### SkRecorder
抽象基类，定义了绘图命令记录器的接口契约。

**继承关系**: 纯虚基类，无父类，由不同后端的具体 Recorder 类继承

**设计模式**:
- 策略模式：不同类型的 Recorder 提供不同的记录策略
- 模板方法模式：定义了记录流程的骨架

**关键成员**:
- 禁用拷贝和移动语义，确保记录器的唯一性和状态一致性

## 公共 API 函数

### 构造与析构

#### `SkRecorder()`
```cpp
SkRecorder() = default;
```
- **功能**: 默认构造函数
- **说明**: 子类负责实际的初始化工作

#### `~SkRecorder()`
```cpp
virtual ~SkRecorder() = default;
```
- **功能**: 虚析构函数，支持多态删除
- **说明**: 确保派生类资源正确释放

### 类型识别

#### `type()`
```cpp
virtual Type type() const = 0;
```
- **功能**: 返回记录器的类型标识
- **返回值**: Type 枚举值，指示具体的后端类型
- **用途**: 运行时类型识别和分发

### CPU 后端访问

#### `cpuRecorder()`
```cpp
virtual skcpu::Recorder* cpuRecorder() = 0;
```
- **功能**: 获取 CPU 后端的记录器实例
- **返回值**: CPU 记录器指针，若当前不是 CPU 后端则可能返回 nullptr
- **用途**: 访问 CPU 特定的记录功能

## 内部实现细节

### 捕获系统（私有接口）

#### `makeCaptureCanvas()`
```cpp
virtual SkCanvas* makeCaptureCanvas(SkCanvas*) = 0;
```
- **功能**: 创建包装了基础画布的捕获画布
- **参数**: 基础画布指针
- **返回值**: 捕获画布指针，若捕获未启用则返回 nullptr
- **说明**: 此函数是私有的，仅供 SkSurface_Base 使用

#### `createCaptureBreakpoint()`
```cpp
virtual void createCaptureBreakpoint(SkSurface*) = 0;
```
- **功能**: 在捕获流程中创建断点标记
- **参数**: 关联的 Surface 指针
- **用途**: 调试和性能分析时标记关键帧

## 枚举类型

### Type
```cpp
enum class Type {
    kCPU,       // CPU 光栅化后端
    kGanesh,    // Ganesh GPU 后端（传统 GPU 架构）
    kGraphite,  // Graphite GPU 后端（新一代 GPU 架构）
};
```

**用途**: 标识记录器所属的渲染后端类型

**设计考量**: 通过类型枚举支持后端特定的优化和功能

## 核心概念

### 绘图命令记录
SkRecorder 的核心职责是记录绘图操作：
- **延迟渲染**: 命令可能不立即执行，而是先记录下来
- **回放**: 记录的命令可以在稍后或不同上下文中重放
- **优化**: 记录阶段可以进行命令合并、剔除等优化

### 多后端支持
Skia 支持多种渲染后端：
- **CPU (kCPU)**: 软件光栅化，跨平台兼容性最好
- **Ganesh (kGanesh)**: 传统 GPU 后端，支持 OpenGL、Vulkan、Metal、D3D
- **Graphite (kGraphite)**: 新一代 GPU 后端，现代化设计，面向未来

### 捕获功能
通过 SkCaptureCanvas 机制记录绘图命令用于调试：
- **命令追踪**: 记录每个绘图调用的参数
- **性能分析**: 标记瓶颈操作
- **可视化调试**: 生成可视化的绘图序列

## 使用场景

### 后端选择
```cpp
// 伪代码示例
SkRecorder* recorder = surface->baseRecorder();
switch (recorder->type()) {
    case SkRecorder::Type::kCPU:
        // CPU 特定优化
        break;
    case SkRecorder::Type::kGanesh:
        // Ganesh GPU 优化
        break;
    case SkRecorder::Type::kGraphite:
        // Graphite GPU 优化
        break;
}
```

### CPU 后端专用功能
```cpp
SkRecorder* recorder = surface->baseRecorder();
if (auto* cpuRec = recorder->cpuRecorder()) {
    // 执行 CPU 后端特定操作
    cpuRec->performCPUOnlyOperation();
}
```

### 调试捕获
```cpp
// 在 SkSurface_Base 内部（友元访问）
SkCanvas* baseCanvas = this->getCanvas();
SkCanvas* captureCanvas = recorder->makeCaptureCanvas(baseCanvas);
if (captureCanvas) {
    // 使用捕获画布进行调试记录
}
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/private/base/SkAPI.h` | API 导出宏定义 |
| `skcpu::Recorder` (前向声明) | CPU 后端记录器类型 |
| `SkCanvas` (前向声明) | 画布类型 |
| `SkSurface` (前向声明) | Surface 类型 |

### 被依赖的模块
- **SkSurface**: 通过 `baseRecorder()` 方法访问记录器
- **SkCanvas**: 绘图命令通过记录器传递给后端
- **后端实现**: skcpu、Ganesh、Graphite 各自实现具体的 Recorder 子类

## 设计模式与设计决策

### 策略模式
SkRecorder 是策略模式的应用：
- **抽象策略**: SkRecorder 定义接口
- **具体策略**: CPU、Ganesh、Graphite 各自的 Recorder 实现
- **上下文**: SkSurface 持有并使用 Recorder

### 抽象工厂模式
不同的 Surface 创建方法产生不同类型的 Recorder：
```cpp
// CPU Surface 创建 CPU Recorder
auto cpuSurface = SkSurfaces::Raster(...);
auto cpuRecorder = cpuSurface->baseRecorder(); // Type::kCPU

// GPU Surface 创建 GPU Recorder
auto gpuSurface = SkSurfaces::RenderTarget(...);
auto gpuRecorder = gpuSurface->baseRecorder(); // Type::kGanesh or kGraphite
```

### 友元访问控制
捕获功能通过友元机制封装：
- **私有接口**: makeCaptureCanvas 和 createCaptureBreakpoint 是私有的
- **友元类**: 只有 SkSurface_Base 可访问
- **设计目的**: 防止外部滥用调试功能，保持 API 清晰

### 接口隔离
cpuRecorder() 方法返回 CPU 特定接口：
- 遵循接口隔离原则
- 避免在基类中暴露所有后端特定方法
- 支持类型安全的后端访问

## 性能考量

### 轻量级设计
SkRecorder 本身是轻量的抽象层：
- 无虚函数表之外的额外开销
- 禁用拷贝避免意外的状态复制
- 类型查询通过简单枚举实现

### 后端优化
通过类型识别允许后端特定优化：
- CPU 后端可使用 SIMD 指令
- GPU 后端可批处理命令
- 不同后端可采用不同的内存布局

### 捕获开销
调试捕获功能设计为可选：
- makeCaptureCanvas 返回 nullptr 时无捕获开销
- 生产环境可完全禁用捕获
- 仅在调试时产生额外开销

## 线程安全

### 非线程安全设计
SkRecorder 禁用拷贝和移动，暗示：
- 不应在多线程间共享实例
- 每个线程应有独立的 Surface 和 Recorder
- 记录操作无锁保护

### 并发记录
若需要并发绘图：
- 创建多个独立的 Surface
- 每个 Surface 拥有独立的 Recorder
- 最后合并结果

## 实现建议

### 子类实现要点
1. **实现 type()**: 返回正确的后端类型
2. **实现 cpuRecorder()**: CPU 后端返回 this，其他返回 nullptr
3. **实现捕获接口**: 根据是否启用调试返回相应的画布
4. **资源管理**: 在析构函数中清理后端资源

### 测试考量
- 类型识别的正确性
- 捕获功能的开关
- 不同后端的行为一致性
- 性能基准测试

## 历史与演进

### 版权信息
文件版权 2025 Google LLC，表明这是最近引入的新接口。

### 现代化设计
使用 C++11/14 特性：
- `= default` 特殊成员函数
- `= delete` 禁用拷贝
- `enum class` 强类型枚举
- `virtual` 和 `override` 显式标记

### Graphite 引入
Type 枚举包含 kGraphite，表明 Skia 正在积极开发新一代 GPU 后端。

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkCanvas.h` | 绘图命令的来源 |
| `include/core/SkSurface.h` | 持有 Recorder 的容器 |
| `src/core/SkSurface_Base.h` | 友元类，访问捕获功能 |
| `include/private/chromium/SkChromeRemoteGlyphCache.h` | 可能使用 skcpu::Recorder |
| Ganesh 后端实现 | GrRecordingContext 相关 |
| Graphite 后端实现 | skgpu::graphite::Recorder |
