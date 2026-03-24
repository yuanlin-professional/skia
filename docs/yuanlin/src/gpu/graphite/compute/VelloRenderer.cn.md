# VelloRenderer

> 源文件: src/gpu/graphite/compute/VelloRenderer.h, src/gpu/graphite/compute/VelloRenderer.cpp

## 概述

`VelloRenderer` 是 Skia Graphite 架构中集成 Vello GPU 加速矢量图形渲染器的接口类。Vello 是一个基于计算着色器的高性能 2D 渲染引擎，使用计算管线而非传统光栅化管线渲染矢量路径。`VelloRenderer` 将 Vello 的计算步骤与 Graphite 的资源管理和命令录制系统集成。

## 架构位置

```
Graphite Vello 集成：
  ├── VelloRenderer（Vello 渲染器）★
  ├── VelloComputeSteps（Vello 计算步骤）
  ├── DispatchGroup（调度组）
  └── ComputePipeline（计算管线）
```

## 主要类与结构体

### VelloRenderer 类

```cpp
class VelloRenderer {
public:
    VelloRenderer(Recorder* recorder);

    // 渲染路径到纹理
    bool renderScene(const VelloScene& scene,
                    const SkIRect& clipRect,
                    sk_sp<TextureProxy> target);

    // 资源管理
    void reset();

private:
    Recorder* fRecorder;
    std::unique_ptr<DispatchGroup> fDispatchGroup;
    // Vello 内部状态...
};
```

## 公共 API 函数

### renderScene

```cpp
bool renderScene(const VelloScene& scene,
                const SkIRect& clipRect,
                sk_sp<TextureProxy> target);
```

**功能**: 将 Vello 场景渲染到目标纹理。

**参数**:
- `scene`: Vello 场景对象（包含路径、填充、描边等）
- `clipRect`: 裁剪矩形
- `target`: 目标渲染纹理

**返回值**: 成功返回 true。

### reset

```cpp
void reset();
```

**功能**: 重置渲染器状态，释放临时资源。

## 内部实现细节

### Vello 渲染管线

Vello 使用多阶段计算管线渲染矢量图形：

1. **路径展平**: 将贝塞尔曲线转换为线段
2. **切片生成**: 将路径切分为水平切片
3. **合并排序**: 按 Y 坐标排序切片
4. **光栅化**: 在每个像素计算覆盖率
5. **合成**: 应用颜色和混合模式

### 与 Graphite 集成

```cpp
bool VelloRenderer::renderScene(...) {
    // 1. 创建 Vello 计算步骤
    auto steps = VelloComputeSteps::Create(scene, clipRect);

    // 2. 构建调度组
    DispatchGroup::Builder builder(fRecorder);
    for (auto& step : steps) {
        builder.appendStep(step.get(), step->resources());
    }
    fDispatchGroup = builder.finalize();

    // 3. 准备资源
    fDispatchGroup->prepareResources(fRecorder->priv().resourceProvider());

    // 4. 记录命令
    fDispatchGroup->addCommands(commandBuffer);

    return true;
}
```

### 资源管理

Vello 需要多个大型缓冲区：
- 路径数据缓冲区
- 切片缓冲区
- 段缓冲区
- 图块缓冲区

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `VelloComputeSteps` | Vello 计算步骤 |
| `DispatchGroup` | 调度组 |
| `Recorder` | 命令录制器 |
| `TextureProxy` | 目标纹理 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Device` | 使用 Vello 渲染路径 |
| `PathRenderer` | 路径渲染策略 |

## 设计模式与设计决策

### 适配器模式

`VelloRenderer` 适配 Vello 的计算管线到 Graphite 的渲染系统。

### 管线抽象

隐藏 Vello 的多阶段计算细节，提供简单的 `renderScene()` 接口。

### 关键设计决策

1. **计算着色器渲染**: 利用 GPU 计算能力加速矢量渲染
2. **场景对象**: Vello 使用不可变场景对象，支持并发构建
3. **显式资源管理**: 调用者负责目标纹理分配
4. **可重置性**: `reset()` 允许复用渲染器实例

## 性能考量

### GPU 加速

Vello 使用计算着色器，充分利用 GPU 并行能力，比传统光栅化快数倍。

### 内存开销

Vello 需要大量临时缓冲区（可能数 MB），但可跨帧复用。

### 适用场景

- **优势**: 复杂矢量图形、大量路径、高分辨率渲染
- **劣势**: 简单图形、小尺寸渲染（开销大于收益）

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/compute/VelloComputeSteps.h` | Vello 计算步骤 |
| `src/gpu/graphite/compute/DispatchGroup.h` | 调度组 |
| `src/gpu/graphite/compute/ComputeStep.h` | 计算步骤抽象 |
| `src/gpu/graphite/Recorder.h` | 命令录制器 |
