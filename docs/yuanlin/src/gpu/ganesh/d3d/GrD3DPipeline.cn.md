# GrD3DPipeline

> 源文件
> - src/gpu/ganesh/d3d/GrD3DPipeline.h

## 概述

`GrD3DPipeline` 是 D3D12 图形管线状态对象的轻量级封装类,继承自 `GrManagedResource`,管理 `ID3D12PipelineState` 的生命周期。该类提供对 D3D12 PSO 的引用计数访问,确保管线对象在使用期间不被销毁。

## 架构位置

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrManagedResource (基类)
    │   └── GrD3DPipeline ← 核心类
    │       └── ID3D12PipelineState (D3D12 COM对象)
    ├── GrD3DPipelineState (使用Pipeline)
    └── GrD3DPipelineStateBuilder (创建Pipeline)
```

## 主要类与结构体

### GrD3DPipeline

**继承关系**:
- 继承自: `GrManagedResource`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPipelineState` | `gr_cp<ID3D12PipelineState>` | D3D12管线状态对象智能指针 |

## 公共 API 函数

```cpp
// 创建管线封装
static sk_sp<GrD3DPipeline> Make(gr_cp<ID3D12PipelineState> pipelineState);

// 获取D3D12管线对象
ID3D12PipelineState* pipelineState() const;
```

## 内部实现细节

### 资源管理

```cpp
class GrD3DPipeline : public GrManagedResource {
public:
    static sk_sp<GrD3DPipeline> Make(gr_cp<ID3D12PipelineState> pso) {
        return sk_sp<GrD3DPipeline>(new GrD3DPipeline(std::move(pso)));
    }
    
    ID3D12PipelineState* pipelineState() const {
        return fPipelineState.get();
    }

private:
    GrD3DPipeline(gr_cp<ID3D12PipelineState> pso)
        : fPipelineState(std::move(pso)) {}
    
    void freeGPUData() const override {
        // gr_cp智能指针自动释放
    }
    
    gr_cp<ID3D12PipelineState> fPipelineState;
};
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrManagedResource` | 资源管理基类 |
| `ID3D12PipelineState` | D3D12管线状态COM接口 |
| `gr_cp<>` | COM智能指针 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DPipelineState` | 持有Pipeline对象 |
| `GrD3DPipelineStateBuilder` | 创建Pipeline对象 |
| `GrD3DCommandList` | 绑定Pipeline到命令列表 |

## 设计模式与设计决策

### 轻量级包装

最小化封装,只提供生命周期管理:
- 低开销
- 简单直接
- 易于理解

### RAII 资源管理

利用智能指针自动管理:
- 防止资源泄漏
- 自动引用计数
- 线程安全

## 性能考量

### 零开销抽象

封装不增加额外开销:
- 内联访问方法
- 无虚函数调用(除基类)
- 直接返回原始指针

### 缓存友好

最小的对象大小:
- 只有智能指针成员
- 减少缓存占用
- 提高访问速度

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrManagedResource.h` | 基类 | 资源管理框架 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 使用者 | 管线状态 |
| `src/gpu/ganesh/d3d/GrD3DPipelineStateBuilder.h/cpp` | 创建者 | 管线构建器 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 类型依赖 | D3D类型定义 |
