# architecture-boundaries

## 必须

- Jesse 只负责信号，不负责执行。
- Executor 只负责执行与状态回写，不负责策略判断。
- 所有关键状态变化必须落库。
- 环境切换必须通过配置文件或环境变量完成。

## 禁止

- Signal Service 直接调用交易所 API。
- Executor 直接嵌入策略逻辑。
- 跨层共享隐式状态。
- 把 backtest、dry-run、tiny live 行为写成分散的 if/else 泥团。

## 例外

- 紧急恢复脚本可跨层只读状态，但必须保留审计记录。
