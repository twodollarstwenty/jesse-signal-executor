import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.summarize_dryrun_account import (
    compute_current_equity,
    compute_realized_pnl,
    compute_unrealized_pnl,
    fetch_current_position,
    fetch_current_price,
)


def compute_notional_usdt(*, qty: float, mark_price: float) -> float:
    return round(qty * mark_price, 2)


def compute_margin_estimate(*, notional_usdt: float, leverage: float) -> float:
    return round(notional_usdt / leverage, 2)


def compute_margin_ratio_estimate(*, margin: float, equity: float) -> float:
    if equity <= 0:
        return 0.0
    return round((margin / equity) * 100, 2)


def render_position_panel(panel: dict) -> str:
    return "\n".join(
        [
            f"符号: {panel['symbol']}",
            f"大小(ETH): {panel['qty']}",
            f"名义金额(USDT): {panel['notional_usdt']}",
            f"保证金: {panel['margin']}",
            f"保证金比率: {panel['margin_ratio']}%",
            f"开仓价格: {panel['entry_price']}",
            f"标记价格: {panel['mark_price']}",
            f"强平价格: {panel['liquidation_price']}",
            f"收益额（收益率）: {panel['pnl_text']}",
            f"止盈/止损: {panel['tp_sl']}",
        ]
    )


def build_current_position_panel(*, initial_capital: float = 1000.0, leverage: float = 10.0, symbol: str = "ETHUSDT") -> dict | None:
    position = fetch_current_position(symbol=symbol)
    if position is None:
        return None

    mark_price = fetch_current_price(symbol=symbol)
    notional_usdt = compute_notional_usdt(qty=position["qty"], mark_price=mark_price)
    margin = compute_margin_estimate(notional_usdt=notional_usdt, leverage=leverage)
    realized_pnl = compute_realized_pnl()
    unrealized_pnl = compute_unrealized_pnl(position=position, current_price=mark_price)
    current_equity = compute_current_equity(
        initial_capital=initial_capital,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
    )
    margin_ratio = compute_margin_ratio_estimate(margin=margin, equity=current_equity)
    side_label = "多" if position["side"] == "long" else "空"

    return {
        "symbol": f"{symbol} 永续",
        "qty": position["qty"],
        "notional_usdt": notional_usdt,
        "margin": margin,
        "margin_ratio": margin_ratio,
        "entry_price": position["entry_price"],
        "mark_price": mark_price,
        "liquidation_price": "--",
        "pnl_text": f"{unrealized_pnl:+.2f} USDT ({((unrealized_pnl / position['entry_price']) * 100) if position['entry_price'] else 0:+.2f}%)",
        "tp_sl": "--",
        "side_label": side_label,
    }


def main() -> None:
    panel = build_current_position_panel()
    if panel is None:
        print("当前无持仓")
        return
    print(render_position_panel(panel))


if __name__ == "__main__":
    main()
