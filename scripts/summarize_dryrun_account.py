import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.shared.db import connect
from scripts.fetch_binance_market_snapshot import fetch_ticker_price


def compute_unrealized_pnl(*, position: dict | None, current_price: float | None) -> float:
    if not position or current_price is None:
        return 0.0
    side = position["side"]
    qty = float(position["qty"])
    entry_price = float(position["entry_price"])
    if side == "short":
        return round((entry_price - current_price) * qty, 2)
    return round((current_price - entry_price) * qty, 2)


def compute_current_equity(*, initial_capital: float, realized_pnl: float, unrealized_pnl: float) -> float:
    return round(initial_capital + realized_pnl + unrealized_pnl, 2)


def compute_realized_pnl_from_signals(rows: list[tuple[str, dict]]) -> float:
    open_position: dict | None = None
    realized = 0.0

    for action, payload in rows:
        payload = payload or {}
        price = float(payload.get("price", 0.0))
        qty = float(payload.get("qty", 1.0))

        if action == "open_long":
            open_position = {"side": "long", "entry_price": price, "qty": qty}
        elif action == "open_short":
            open_position = {"side": "short", "entry_price": price, "qty": qty}
        elif action == "close_long" and open_position and open_position["side"] == "long":
            realized += (price - open_position["entry_price"]) * open_position["qty"]
            open_position = None
        elif action == "close_short" and open_position and open_position["side"] == "short":
            realized += (open_position["entry_price"] - price) * open_position["qty"]
            open_position = None

    return round(realized, 2)


def render_account_summary(*, initial_capital: float, realized_pnl: float, unrealized_pnl: float, current_equity: float, position: dict | None, current_price: float | None) -> str:
    lines = [
        f"初始资金: {initial_capital:.2f}",
        f"已实现盈亏: {realized_pnl:+.2f}",
        f"未实现盈亏: {unrealized_pnl:+.2f}",
        f"当前权益: {current_equity:.2f}",
    ]
    if position:
        lines.extend(
            [
                f"当前持仓: {position['side']}",
                f"持仓数量: {position['qty']}",
                f"开仓价: {position['entry_price']}",
                f"当前价: {current_price:.2f}",
            ]
        )
    else:
        lines.append("当前持仓: flat")
    return "\n".join(lines)


def fetch_current_position(symbol: str = "ETHUSDT", *, instance_id: str | None = None) -> dict | None:
    def query_row(*, sql: str, params: tuple) -> tuple | None:
        conn = connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        finally:
            conn.close()

    row = None
    can_use_instance_filter = instance_id is not None
    if instance_id is not None:
        try:
            row = query_row(
                sql="""
                    SELECT side, qty, entry_price
                    FROM position_state
                    WHERE instance_id = %s AND symbol = %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                params=(instance_id, symbol),
            )
        except Exception as exc:
            if 'instance_id' not in str(exc):
                raise
            can_use_instance_filter = False

    if not can_use_instance_filter:
        row = query_row(
            sql="""
                SELECT side, qty, entry_price
                FROM position_state
                WHERE symbol = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
            params=(symbol,),
        )

    if row is None:
        return None
    side, qty, entry_price = row
    if side == "flat":
        return None
    return {"side": side, "qty": float(qty), "entry_price": float(entry_price)}


def fetch_current_price(symbol: str = "ETHUSDT") -> float:
    snapshot = fetch_ticker_price(symbol=symbol)
    return float(snapshot["price"])


def compute_realized_pnl(*, instance_id: str | None = None) -> float:
    def query_rows(*, sql: str, params: tuple | None = None) -> list[tuple[str, dict]]:
        conn = connect()
        try:
            with conn, conn.cursor() as cur:
                if params is None:
                    cur.execute(sql)
                else:
                    cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    rows = []
    can_use_instance_filter = instance_id is not None
    if instance_id is not None:
        try:
            rows = query_rows(
                sql="""
                    SELECT action, payload_json
                    FROM signal_events
                    WHERE status = 'execute' AND instance_id = %s
                    ORDER BY signal_time ASC, id ASC
                    """,
                params=(instance_id,),
            )
        except Exception as exc:
            if 'instance_id' not in str(exc):
                raise
            can_use_instance_filter = False

    if not can_use_instance_filter:
        rows = query_rows(
            sql="""
                SELECT action, payload_json
                FROM signal_events
                WHERE status = 'execute'
                ORDER BY signal_time ASC, id ASC
                """
        )

    return compute_realized_pnl_from_signals(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-capital", type=float, default=1000.0)
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--instance-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    position = fetch_current_position(symbol=args.symbol, instance_id=args.instance_id)
    current_price = fetch_current_price(symbol=args.symbol)
    realized_pnl = compute_realized_pnl(instance_id=args.instance_id)
    unrealized_pnl = compute_unrealized_pnl(position=position, current_price=current_price)
    current_equity = compute_current_equity(
        initial_capital=args.initial_capital,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
    )
    print(
        render_account_summary(
            initial_capital=args.initial_capital,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            current_equity=current_equity,
            position=position,
            current_price=current_price,
        )
    )


if __name__ == "__main__":
    main()
