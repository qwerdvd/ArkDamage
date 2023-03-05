<div style="text-align: center">
  <img width="200" src="https://v2.nonebot.dev/logo.png" alt="logo">

# ArkDamage

_✨基于 [nonebot2](https://github.com/nonebot/nonebot2) 和 [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)的**Arknights**干员 DPS 计算器✨_

</div>

<div style="text-align: center">
  <a href="https://raw.githubusercontent.com/cscs181/QQ-Github-Bot/master/LICENSE">
    <img src="https://img.shields.io/github/license/cscs181/QQ-Github-Bot.svg" alt="license">
  </a>
  <a href="https://img.shields.io/badge/nonebot-2.0.0rc1+-red.svg">
    <img src="https://img.shields.io/badge/nonebot-2.0.0rc1+-red.svg" alt="nonebot">
  </a>
  <img src="https://img.shields.io/badge/python-3.10.0+-blue.svg" alt="python">
</div>

## 安装
**插件仍在开发中，遇到问题还请务必提 issue。**

- #### 直接 git clone（建议）

```bash
$ git clone https://ghproxy.com/https://github.com/qwerdvd/ArkDamage.git --depth=1
```

- #### ~~使用 pip/nb-cli 安装（画饼中）~~

## 安装依赖(二选一即可)

- ##### 使用 pip 安装依赖

```bash
$ pip install -r requirements.txt
```

- #### 使用 poetry 安装依赖

```bash
$ poetry install
```

## 使用方法

**使用前请先确保命令前缀为空，否则请在以下命令前加上命令前缀（默认为`/`）。**

- `伤害计算 能天使 满潜 精二90 三技能 一模` 进行干员 DPS 计算
- `干员曲线 能天使 满潜 精二90 三技能 一模` 进行干员伤害曲线的计算
- `设置敌人 杰斯顿·威廉姆斯 1个` 进行敌人设置，一个群只能设置一个敌人，且只有管理员可以更改

## 注意事项
- 由于使用 `match/case` 语法 请使用 `python3.10.0+` 运行

## TODO
- [ ] 优化代码
- [ ] 使用图片发送

## 本插件改自
[DPS计算器](https://github.com/xulai1001/akdata)
