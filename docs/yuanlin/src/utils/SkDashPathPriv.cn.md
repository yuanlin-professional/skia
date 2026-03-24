# SkDashPathPriv

> 源文件: src/utils/SkDashPathPriv.h

## 概述

`SkDashPathPriv` 包含虚线路径效果的内部实用函数,为 `SkDashPathEffect` 提供底层实现。

## 架构位置

作为路径效果的私有实现,处理虚线模式的应用和路径分段。

## 主要功能

- 路径测量和分段
- 虚线间隔计算
- 相位偏移处理
- 优化的虚线应用算法

## 设计决策

提供高效的虚线生成算法,支持各种路径类型。处理边界情况(如非常短的虚线)。

## 相关文件

- `src/effects/SkDashPathEffect.cpp`: 虚线路径效果
- `include/core/SkPathEffect.h`: 路径效果基类
