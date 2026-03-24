# scripts 资产下载脚本

> 源文件: infra/bots/assets/scripts/download.py

## 概述

通用的资产下载脚本，通过 common 模块调用资产管理系统的下载功能。该脚本从 CIPD 下载指定版本的资产到本地，供开发或测试使用。

## 架构位置

位于 `infra/bots/assets/scripts/`，是资产管理工作流的标准组件。每个资产包都包含相同的 download.py。

## 主要类与结构体

极简脚本，只有导入和调用。

## 公共 API 函数

脚本作为主程序执行：
```python
if __name__ == '__main__':
    common.run('download')
```

`common.run('download')` 会：
1. 确定资产名称
2. 读取 VERSION 文件获取资产版本
3. 从 CIPD 下载对应版本的资产
4. 解压到指定目录

## 内部实现细节

### 版本管理

下载的版本由同目录的 VERSION 文件指定，该文件包含 CIPD 实例 ID 或版本标签。

### 缓存机制

CIPD 客户端会缓存已下载的资产，避免重复下载。

## 设计模式与设计决策

与 upload.py 对称的代理模式，提供统一的下载接口。

## 相关文件

- `common.py`: 提供 run() 函数
- `VERSION`: 指定下载的资产版本
- `infra/bots/assets/assets.py`: 下载实现
