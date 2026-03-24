# binary-size - 二进制体积分析镜像

## 概述

用于构建 Skia 代码体积树状图的 Docker 镜像。包含二进制分析工具，可生成交互式的代码体积可视化。

## 目录结构

```
binary-size/
└── Dockerfile   # Docker 镜像定义
```

## 使用方法

```bash
docker build -t binary-size ./binary-size/
docker run -v $SKIA_ROOT/out/Release:/IN -v /tmp/output:/OUT binary-size \
  /opt/binary_size/src/run_binary_size_analysis.py --library /IN/skottie_tool --destdir /OUT
```

## 依赖关系

- Skia 编译产物

## 相关文档与参考

- `infra/bots/buildstats/` - 构建统计脚本
