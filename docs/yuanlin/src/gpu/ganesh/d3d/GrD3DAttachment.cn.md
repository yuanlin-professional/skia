# GrD3DAttachment

> 源文件: src/gpu/ganesh/d3d/GrD3DAttachment.h, src/gpu/ganesh/d3d/GrD3DAttachment.cpp

## 概述

`GrD3DAttachment` 是 Skia Ganesh Direct3D 12 后端中实现的附件(Attachment)类,主要用于模板附件(Stencil Attachment)。它继承自 `GrAttachment` 和 `GrD3DTextureResource`,封装了 D3D12 的深度/模板纹理资源及其视图,为渲染管线提供模板测试和深度测试功能。

## 架构位置

`GrD3DAttachment` 位于 D3D12 渲染资源层:
- **基类**: `GrAttachment` (跨平台附件抽象), `GrD3DTextureResource` (D3D12 纹理资源)
- **用途**: 作为渲染目标的模板/深度附件
- **协作**: 与 `GrD3DGpu` 和渲染管线交互

## 主要类与结构体

### GrD3DAttachment 类
```cpp
class GrD3DAttachment : public GrAttachment, public GrD3DTextureResource {
public:
    static sk_sp<GrD3DAttachment> MakeStencil(GrD3DGpu* gpu,
                                              SkISize dimensions,
                                              int sampleCnt,
                                              DXGI_FORMAT format);

    GrBackendFormat backendFormat() const override;
    D3D12_CPU_DESCRIPTOR_HANDLE view() const;

protected:
    void onRelease() override;
    void onAbandon() override;
    void onSetLabel() override;
};
```

**继承关系**:
- 基类 1: `GrAttachment` -> `GrSurface` -> `GrGpuResource`
- 基类 2: `GrD3DTextureResource`
- 多重继承: 同时具有附件和 D3D12 纹理资源的特性

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fView` | `GrD3DDescriptorHeap::CPUHandle` | 深度/模板视图(DSV) |
| `fFormat` | `DXGI_FORMAT` | D3D12 格式(如 `DXGI_FORMAT_D24_UNORM_S8_UINT`) |

继承自 `GrD3DTextureResource`:
- `fResource`: D3D12 资源对象
- `fResourceState`: 资源状态管理

## 公共 API 函数

### 工厂方法

**MakeStencil**
```cpp
static sk_sp<GrD3DAttachment> MakeStencil(GrD3DGpu* gpu,
                                          SkISize dimensions,
                                          int sampleCnt,
                                          DXGI_FORMAT format);
```
创建模板附件。流程:
1. 设置资源描述(2D 纹理,深度/模板标志)
2. 初始化纹理资源信息
3. 创建深度/模板视图(DSV)
4. 返回 `GrD3DAttachment` 对象

支持的格式:
- `DXGI_FORMAT_D24_UNORM_S8_UINT`: 24位深度 + 8位模板
- `DXGI_FORMAT_D32_FLOAT_S8X24_UINT`: 32位深度 + 8位模板 + 24位填充

### 访问器

**backendFormat**
```cpp
GrBackendFormat backendFormat() const override;
```
返回 Ganesh 后端格式封装。

**view**
```cpp
D3D12_CPU_DESCRIPTOR_HANDLE view() const;
```
获取 DSV (Depth Stencil View) 句柄,用于绑定到渲染管线。

## 内部实现细节

### 资源创建

```cpp
D3D12_RESOURCE_DESC resourceDesc = {
    .Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D,
    .Alignment = 0,  // 默认对齐
    .Width = dimensions.width(),
    .Height = dimensions.height(),
    .DepthOrArraySize = 1,
    .MipLevels = 1,
    .Format = format,
    .SampleDesc = {.Count = sampleCnt, .Quality = DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN},
    .Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN,  // 驱动选择最优布局
    .Flags = D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL  // 允许作为深度/模板
};
```

**关键点**:
- **Layout = UNKNOWN**: 让驱动选择最优的 swizzle 布局
- **ALLOW_DEPTH_STENCIL**: 必需标志,允许作为深度/模板目标
- **SampleDesc**: 支持 MSAA,Quality 使用标准多采样模式

### 清除值

```cpp
D3D12_CLEAR_VALUE clearValue = {
    .Format = format,
    .DepthStencil = {.Depth = 0, .Stencil = 0}
};
```
初始清除值为 0,表示深度最近,模板值为 0。

### DSV 创建

```cpp
GrD3DDescriptorHeap::CPUHandle view =
    gpu->resourceProvider().createDepthStencilView(info.fResource.get());
```
由 `GrD3DResourceProvider` 负责从描述符堆分配 DSV。

### 资源状态

初始状态为 `D3D12_RESOURCE_STATE_DEPTH_WRITE`:
- 表示深度/模板缓冲区可写
- 渲染时通常需要此状态
- 读取时(如作为纹理)需要转换到 `DEPTH_READ`

### 生命周期管理

**onRelease**
```cpp
void onRelease() {
    GrD3DGpu* gpu = this->getD3DGpu();
    this->releaseResource(gpu);  // 继承自 GrD3DTextureResource
    GrAttachment::onRelease();
}
```
释放 D3D12 资源和视图。

**onAbandon**
```cpp
void onAbandon() {
    this->releaseResource();  // 不通知 GPU,直接释放
    GrAttachment::onAbandon();
}
```
上下文丢失时调用,不执行 GPU 操作。

### Label 设置

**onSetLabel**
```cpp
void onSetLabel() override;
```
设置 D3D12 资源的调试名称,便于 GPU 调试工具(如 PIX)识别。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrAttachment` | 基类,跨平台附件抽象 |
| `GrD3DTextureResource` | 基类,D3D12 纹理资源管理 |
| `GrD3DGpu` | GPU 实现,资源操作 |
| `GrD3DResourceProvider` | 创建描述符视图 |
| `GrD3DDescriptorHeap` | 描述符堆管理 |
| `ID3D12Resource` | D3D12 资源对象 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrD3DGpu` | 使用 `GrD3DAttachment` 作为模板附件 |
| `GrD3DRenderTarget` | 关联模板附件到渲染目标 |

## 设计模式与设计决策

### 设计模式

1. **多重继承**: 同时继承附件和纹理资源特性
2. **工厂方法**: `MakeStencil` 静态工厂创建特定类型附件
3. **RAII**: 资源生命周期由智能指针管理

### 设计决策

**为什么多重继承?**
- `GrAttachment`: 提供附件通用接口(尺寸、用途、采样数)
- `GrD3DTextureResource`: 提供 D3D12 资源管理(状态转换、释放)
- 避免代码重复,复用两个基类的功能

**为什么只提供 MakeStencil?**
- D3D12 中深度和模板通常打包在一起
- Skia 主要使用模板缓冲区进行裁剪
- 深度缓冲区在 2D 渲染中较少使用

**为什么使用 CPU 描述符句柄?**
- DSV 是渲染目标视图,只需要 CPU 句柄
- 不需要着色器访问,无需 GPU 可见描述符堆
- 节省宝贵的 GPU 可见描述符堆空间

**Layout = UNKNOWN 的意义**
- 不同 GPU 对深度/模板布局有不同的优化
- `UNKNOWN` 让驱动选择最优布局
- 应用程序无法直接读取数据(需要通过 CopyResource)

**标准多采样质量模式**
- `DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN`: D3D12 定义的标准模式
- 所有支持 MSAA 的硬件都支持此模式
- 自定义质量模式需要查询硬件能力

## 性能考量

### 优化策略

1. **驱动优化布局**: `UNKNOWN` 布局让驱动优化内存访问
2. **分离深度和模板**: 如果只需要模板,可以使用纯模板格式(D3D12 不支持,需要打包)
3. **MSAA 质量**: 标准模式性能最好
4. **资源复用**: 相同尺寸和格式的附件可以在不同渲染目标间共享

### 性能特征

**深度/模板格式性能**:
- `D24_UNORM_S8_UINT`: 32位对齐,硬件友好
- `D32_FLOAT_S8X24_UINT`: 64位,精度高但带宽大

**MSAA 开销**:
- 2x/4x MSAA: 适中开销
- 8x MSAA: 高开销,慎用

**内存占用**:
- 1920x1080 @ D24S8 @ 1x = ~8 MB
- 1920x1080 @ D24S8 @ 4x = ~32 MB

### 性能陷阱

- **过大的附件**: 匹配实际渲染目标尺寸
- **不必要的清除**: 如果完全覆盖,可以使用 discard hint
- **状态转换**: 深度/模板附件在 DEPTH_WRITE 和 DEPTH_READ 间切换有开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrAttachment.h/.cpp` | 基类 | 跨平台附件抽象 |
| `src/gpu/ganesh/d3d/GrD3DTextureResource.h` | 基类 | D3D12 纹理资源 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/.cpp` | 使用者 | GPU 实现 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h` | 依赖 | 描述符堆 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h` | 协作 | 渲染目标 |
