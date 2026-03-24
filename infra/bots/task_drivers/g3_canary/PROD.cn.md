G3 金丝雀生产手册
===========================

关于金丝雀 (Canary) 的一般信息可在 [go/autoroller-canary-bots](https://goto.google.com/autoroller-canary-bots) 中找到。

告警
======

g3_canary_infra_failures
------------------------

当 G3 中的 skia_try_service 返回异常时触发。
请在 [go/skia-borg-jobs](go/skia-borg-jobs) 中查看 skia_try_service 的错误日志。

对于看起来不是暂时性的错误，过去重启 borg 作业 (Job) 有效：
```
 borg --borg=${BORG_CELL} --user=skia --name=skia_try_service --avoid_parent restarttask 0
```
