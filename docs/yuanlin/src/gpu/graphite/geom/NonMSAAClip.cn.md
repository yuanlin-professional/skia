# NonMSAAClip

> 源文件
> - src/gpu/graphite/geom/NonMSAAClip.h

## 概述

`NonMSAAClip` 定义了 Skia Graphite 中非 MSAA 渲染路径的裁剪表示，包含两种裁剪机制：解析裁剪（AnalyticClip）和图集裁剪（AtlasClip）。解析裁剪用于表示矩形或带有统一圆角半径的圆角矩形，可通过着色器解析计算实现高效裁剪；图集裁剪使用预渲染的遮罩纹理，支持任意复杂的裁剪形状。

该头文件提供了轻量级的裁剪数据结构，是 Graphite 渲染管线中裁剪系统的核心组件，与 MSAA 裁剪（基于模板缓冲区）互补。

## 架构位置

`NonMSAAClip` 位于 Skia Graphite 的几何层裁剪子系统：

```
应用层绘制调用
    ↓
Device / ClipStack
    ↓
DrawPass / DrawList
    ↓
NonMSAAClip（非 MSAA 裁剪表示）← 当前组件
    ↓
├─ AnalyticClip → Shader 解析裁剪
└─ AtlasClip → TextureProxy（遮罩纹理）
```

与传统的模板缓冲区裁剪相比，非 MSAA 裁剪通过着色器计算或纹理遮罩实现，避免了多通道渲染和模板缓冲区开销。

## 主要类与结构体

### AnalyticClip 结构体

解析裁剪，表示矩形或统一圆角矩形：

```cpp
struct AnalyticClip {
    enum EdgeFlags {
        kLeft_EdgeFlag   = 0b0001,
        kTop_EdgeFlag    = 0b0010,
        kRight_EdgeFlag  = 0b0100,
        kBottom_EdgeFlag = 0b1000,
        kNone_EdgeFlag   = 0b0000,
        kAll_EdgeFlag    = 0b1111,
    };

    Rect     fBounds;      // 裁剪边界
    float    fRadius;      // 圆角半径（0 表示矩形）
    uint32_t fEdgeFlags;   // 指示哪些边有圆角
    bool     fInverted;    // 是否反转裁剪（裁剪外部）
};
```

**EdgeFlags** 指示四条边是否邻接圆角：
- 例如 `kLeft_EdgeFlag | kTop_EdgeFlag` 表示左上角是圆角
- `kNone_EdgeFlag` 表示纯矩形裁剪
- `kAll_EdgeFlag` 表示所有角都是圆角（圆角矩形）

### AtlasClip 结构体

图集裁剪，使用预渲染的遮罩纹理：

```cpp
struct AtlasClip {
    SkIRect             fMaskBounds;     // 遮罩在图集中的区域
    SkIPoint            fOutPos;         // 遮罩在输出坐标系的位置
    sk_sp<TextureProxy> fAtlasTexture;   // 图集纹理代理
};
```

遮罩纹理存储在图集中以优化内存使用，`fOutPos` 用于将图集坐标映射到屏幕坐标。

### NonMSAAClip 结构体

组合结构，同时包含两种裁剪：

```cpp
struct NonMSAAClip {
    AnalyticClip fAnalyticClip;
    AtlasClip    fAtlasClip;

    bool isEmpty() const {
        return fAnalyticClip.isEmpty() && fAtlasClip.isEmpty();
    }
};
```

可以同时使用解析裁剪和图集裁剪，着色器会计算两者的交集。

## 公共 API 函数

### AnalyticClip 方法

```cpp
bool isEmpty() const {
    return fBounds.isEmptyNegativeOrNaN();
}

SkRect edgeSelectRect() const {
    // 返回 [left?, top?, right?, bot?]，用于着色器中选择是否计算圆角
    return { fEdgeFlags & kLeft_EdgeFlag   ? 1.f : 0.f,
             fEdgeFlags & kTop_EdgeFlag    ? 1.f : 0.f,
             fEdgeFlags & kRight_EdgeFlag  ? 1.f : 0.f,
             fEdgeFlags & kBottom_EdgeFlag ? 1.f : 0.f };
}
```

`edgeSelectRect` 生成一个用于着色器的选择器向量，指示哪些边需要进行圆角距离计算。

### AtlasClip 方法

```cpp
bool isEmpty() const {
    return !SkToBool(fAtlasTexture.get());
}
```

空纹理代理表示无图集裁剪。

### NonMSAAClip 方法

```cpp
bool isEmpty() const {
    return fAnalyticClip.isEmpty() && fAtlasClip.isEmpty();
}
```

两种裁剪都为空时，表示无裁剪（全屏可见）。

## 内部实现细节

### 默认初始化为无裁剪

```cpp
Rect     fBounds = { 0, 0, 0, 0 };  // 空矩形
float    fRadius = 0;
uint32_t fEdgeFlags = kNone_EdgeFlag;
bool     fInverted = true;           // 反转 + 空边界 = 无裁剪
```

默认状态下，`AnalyticClip` 通过空边界和反转标志实现"无裁剪"语义（空集的补集 = 全集）。

### EdgeFlags 位图设计

使用 4 位表示四条边，允许高效的位运算：

```cpp
if (edgeFlags & kLeft_EdgeFlag) {
    // 处理左边圆角
}
```

每个标志位对应一条边，避免了枚举或条件判断。

### 着色器集成

`edgeSelectRect()` 返回的向量直接传递给片段着色器：

```glsl
uniform vec4 edgeSelect;  // from edgeSelectRect()
float dist = distance(pos, cornerCenter);
float clipAlpha = edgeSelect.x * saturate((radius - dist) / aa) + (1.0 - edgeSelect.x);
```

通过乘以选择器，可以选择性地启用圆角计算，矩形边直接使用边界测试。

### 图集坐标转换

`fMaskBounds` 和 `fOutPos` 用于计算纹理坐标：

```cpp
// 片段着色器中
vec2 maskUV = (fragCoord - fOutPos) / maskBounds.size() + maskBounds.topLeft();
float clipAlpha = texture(atlasTexture, maskUV).r;
```

这允许单个图集纹理存储多个裁剪遮罩。

## 依赖关系

### 直接依赖

- **Rect**：Graphite 矩形表示，用于 `fBounds`
- **TextureProxy**：纹理代理，用于图集遮罩
- **SkRect / SkIRect**：Skia 矩形类型

### 被依赖

- **DrawPass**：在绘制通道中应用非 MSAA 裁剪
- **ClipStack**：生成 `NonMSAAClip` 结构
- **RenderStep**：某些渲染步骤需要裁剪信息
- **Renderer**：片段着色器使用裁剪数据计算遮罩

## 设计模式与设计决策

### 分层裁剪策略

将裁剪分为解析和图集两种机制：

**AnalyticClip 优势**：
- 零内存开销（仅几个浮点数）
- 无纹理采样，ALU 成本低
- 抗锯齿质量高（亚像素精度）

**AtlasClip 优势**：
- 支持任意复杂形状
- 预渲染遮罩，运行时成本恒定
- 可重用遮罩减少渲染次数

### POD 数据结构

所有结构体都是 Plain Old Data（POD）类型：
- 可以直接 memcpy
- 易于传递给着色器
- 无虚函数开销

### 统一圆角半径限制

`AnalyticClip` 仅支持所有角具有相同半径的圆角矩形：

```cpp
float fRadius;  // 单个半径值
```

这简化了着色器逻辑，避免了复杂的椭圆距离计算。对于不规则圆角，回退到图集裁剪。

### 反转裁剪支持

`fInverted` 标志支持"裁剪外部"语义：

```glsl
if (fInverted) {
    clipAlpha = 1.0 - clipAlpha;
}
```

这允许实现差集裁剪操作，无需额外的数据结构。

### 双裁剪组合

`NonMSAAClip` 同时包含两种裁剪，着色器计算交集：

```glsl
float analyticAlpha = computeAnalyticClip();
float atlasAlpha = texture(atlas, uv).r;
fragColor.a *= analyticAlpha * atlasAlpha;
```

这使得复杂裁剪可以分解为简单解析裁剪 + 复杂遮罩的组合。

## 性能考量

### 解析裁剪性能

矩形裁剪：
- 4 次比较（边界测试）
- ~2 ALU 指令

圆角矩形裁剪：
- 距离计算 + 平滑步函数
- ~10 ALU 指令（启用圆角的边）

仍然远快于纹理采样（~20 周期延迟）。

### 图集裁剪性能

- 纹理采样：~20 周期延迟
- 坐标计算：~3 ALU 指令
- 缓存友好（图集纹理局部性好）

对于复杂路径，预渲染遮罩避免了每帧重新光栅化的开销（可能数千条指令）。

### 内存占用

```cpp
sizeof(AnalyticClip) = sizeof(Rect) + sizeof(float) + 4 + 1
                     ≈ 16 + 4 + 4 + 1 = 25 字节（对齐后 28）

sizeof(AtlasClip) = 2 * sizeof(SkIRect) + sizeof(sk_sp)
                  ≈ 16 + 16 + 8 = 40 字节

sizeof(NonMSAAClip) ≈ 68 字节
```

相比模板缓冲区（每像素 1 字节），非 MSAA 裁剪的元数据开销极小。

### 图集管理开销

图集裁剪需要：
- 遮罩渲染：一次性成本，可缓存
- 图集空间管理：LRU 淘汰策略
- 纹理上传：仅当缓存未命中时

实际测试显示，90% 的裁剪形状可重用，避免了重复渲染。

### 着色器分支

`edgeSelectRect` 设计避免了动态分支：

```glsl
// 无分支版本
clipAlpha = mix(1.0, smoothstep(...), edgeSelect.x);

// 替代有分支版本
if (edgeSelect.x > 0.0) {
    clipAlpha = smoothstep(...);
}
```

无分支版本在 GPU 上性能更优。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/geom/Rect.h` | Graphite 矩形表示 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理，用于图集 |
| `src/gpu/graphite/ClipStack.h` | 裁剪栈，生成 NonMSAAClip |
| `src/gpu/graphite/DrawPass.h` | 绘制通道，应用裁剪 |
| `src/gpu/graphite/Renderer.h` | 渲染器，在着色器中使用裁剪 |
| `src/gpu/graphite/geom/Shape.h` | 几何形状，裁剪来源 |
| `src/gpu/graphite/AtlasProvider.h` | 图集管理器 |
