# Skia Debugger 调试器工具

## 概述

`tools/debugger` 提供了 Skia 绘图命令的调试基础设施。它能够录制、回放和逐步执行 SkCanvas 的绘图命令，是 Skia 调试器前端（debugger.skia.org）的核心后端实现。该工具支持 SKP（Skia Picture）和 MSKP（多帧 Skia Picture）文件的分析，允许开发者逐条检查绘图操作、查看中间渲染状态、以及将命令序列化为 JSON 格式。

## 目录结构

```
tools/debugger/
├── BUILD.bazel              # Bazel 构建配置
├── DebugCanvas.cpp          # 调试画布核心实现（约 25KB）
├── DebugCanvas.h            # 调试画布类声明
├── DebugLayerManager.cpp    # 离屏层管理器实现
├── DebugLayerManager.h      # 离屏层管理器声明
├── DrawCommand.cpp          # 绘图命令封装实现（约 78KB，最大文件）
├── DrawCommand.h            # 绘图命令类层次结构定义
├── JsonWriteBuffer.cpp      # JSON 序列化写缓冲区
└── JsonWriteBuffer.h        # JSON 写缓冲区声明
```

## 核心组件

### DebugCanvas

`DebugCanvas` 继承自 `SkCanvasVirtualEnforcer<SkCanvas>`，是调试功能的核心类：

- **命令录制**: 拦截所有 Canvas 操作，将其包装为 `DrawCommand` 对象存储
- **选择性回放**: 支持设定回放起止点，可跳过或仅执行特定命令
- **可视化辅助**: 可叠加裁剪区域高亮、操作范围显示等调试信息
- **MSKP 支持**: 配合 `DebugLayerManager` 解析多层动画帧

### DrawCommand

`DrawCommand` 定义了完整的 Skia 绘图操作类型枚举，包括但不限于：

| 操作类型 | 说明 |
|---------|------|
| `kClear_OpType` | 清除画布 |
| `kClipPath_OpType` | 路径裁剪 |
| `kDrawImage_OpType` | 绘制图像 |
| `kDrawPath_OpType` | 绘制路径 |
| `kDrawRect_OpType` | 绘制矩形 |
| `kDrawTextBlob_OpType` | 绘制文本块 |
| `kConcat44_OpType` | 4x4 矩阵变换连接 |
| `kSave_OpType / kRestore_OpType` | 保存/恢复画布状态 |

每个 `DrawCommand` 子类都实现了：
- `execute()` - 在目标 Canvas 上执行操作
- `toJSON()` - 序列化为 JSON 格式（供前端展示）
- `render()` - 仅渲染当前命令的效果

### DebugLayerManager

专门处理 MSKP（多帧 SKP）文件中的离屏层：

- 管理每个 RenderNode ID 对应的 SkPicture 集合
- 按帧号和命令索引渲染指定层的中间状态
- 支持脏区域（dirty region）追踪，实现增量渲染
- 提供层的 SkImage 快照，用于调试器 UI 展示

### JsonWriteBuffer

实现 `SkWriteBuffer` 接口，将 Skia 内部数据结构序列化为 JSON：

- 支持 SkPaint、SkMatrix、SkPath 等核心类型的 JSON 转换
- 使用 `SkJSONWriter` 输出结构化 JSON 数据
- 配合 `UrlDataManager` 管理二进制资源（如图片）的 URL 引用

## 工作流程

```
SKP/MSKP 文件 --> SkPicture::playback() --> DebugCanvas（录制命令）
                                                    |
                                        DrawCommand 数组
                                                    |
                                    ├── 逐步回放到目标 Canvas
                                    ├── toJSON() 序列化
                                    └── GrAuditTrail GPU 操作审计
```

## 构建

```bash
# Bazel 构建
bazel build //tools/debugger:debugger
```

## 与其他模块的关系

- **modules/canvaskit/**: CanvasKit 内嵌了 debugger 模块，支持 Web 端调试
- **tools/skp/**: 提供 SKP 文件的录制和页面集管理
- **debugger.skia.org**: Web 前端调试界面，调用本模块的 WASM 编译版本
