资产
======

此目录包含管理构建机器人使用的资产的工具。主要入口点是 assets.py，它允许用户添加、删除、上传和下载资产。

资产存储在 Google Storage 中，以版本号命名。


各个资产
-----------------

每个资产都有自己的子目录，包含以下内容：
* VERSION：资产的当前版本号。
* [可选] create.py：创建资产的脚本，由用户实现，由 `sk asset upload` 调用。
* [可选] create\_and\_upload.py：用户实现的便捷脚本，以适合该资产的方式封装 `sk asset upload`。


示例
-------

与所有 `sk asset` 的使用一样，以下操作仅在您拥有 google.com 帐户并已通过
`gcloud auth application-default login` 完成身份验证后才有效。

添加新资产并上传初始版本。

```
$ sk asset add myasset
Do you want to add a creation script for this asset? (y/n): n
$ sk asset upload --in ${MY_ASSET_LOCATION} myasset
$ git commit
```

添加一个可以自动创建的资产。

```
$ sk asset add myasset
Do you want to add a creation script for this asset? (y/n): y
Created infra/bots/assets/myasset/create.py; you will need to add implementation before uploading the asset.
$ vi infra/bots/assets/myasset/create.py
(implement the create_asset function)
$ sk asset upload myasset
$ git commit
```

更新资产。

```
(update the create.py script)
$ sk asset upload myasset
(assuming infra/bots/assets/myasset/VERSION has been updated by the previous
 command, regenerate tasks.json per infra/bots/README:)
$ make -C infra/bots train
$ git commit
```
