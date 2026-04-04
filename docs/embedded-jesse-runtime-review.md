# 内嵌 Jesse Runtime 方案复核

## 结论

当前 `Ott2butKAMA` 的真实源码已经证明：它不是普通 Python 模块，而是 Jesse runtime 依赖型策略。

因此，不能继续用“主项目 `.venv` 直接 import 策略源码”的方式验证接入是否成功。

下一步正确顺序应该调整为：

1. 先建立新项目自己的 Jesse runtime bootstrap
2. 再把 `Ott2butKAMA` 和完整指标依赖同步进去
3. 最后在 Jesse runtime 环境中验证策略和桥接是否可用

## 已确认的问题

### 1. 策略依赖 Jesse runtime

`Ott2butKAMA` 直接依赖：

- `talib`
- `jesse`
- `jesse.helpers`
- `jesse.strategies`

这意味着它不能被当作普通 Python 业务模块直接在主项目应用层环境中导入验证。

### 2. 指标依赖未完整同步

当前复制进新项目的 `custom_indicators_ottkama` 还不完整。

策略依赖链至少包括：

- `ott.py`
- `var.py`
- `ewo.py`
- `rma.py`
- `cae.py`

若不完整复制，导入验证必然继续失败。

### 3. 当前验证环境定义不对

当前“导入测试”放在主项目 `.venv` 中执行，这个验证层级不正确。

正确的验证层级应该是：

- 在 `runtime/jesse_workspace` 的 Jesse 环境中验证策略可导入
- 在 Jesse runtime 中验证桥接模块可导入

## 调整建议

后续实现顺序应该变成：

### 第一阶段

- 建立 `runtime/jesse_workspace`
- 为 Jesse runtime 准备独立 Python 环境
- 安装 Jesse 依赖与 `TA-Lib`

### 第二阶段

- 同步 `Ott2butKAMA` 的完整策略源码与完整指标依赖

### 第三阶段

- 在 Jesse runtime 内验证策略 import 成功
- 在 Jesse runtime 内验证桥接模块 import 成功

### 第四阶段

- 再去接开仓 / 平仓真实信号写库

## 结果

这意味着“把真实策略文件先复制进来”这一步本身没有错，但它不能再作为“已成功接入”的验收标准。

新的验收标准必须建立在 Jesse runtime bootstrap 完成之后。
