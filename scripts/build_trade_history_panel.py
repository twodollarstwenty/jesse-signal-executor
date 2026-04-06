import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.shared.db import connect


def translate_action_label(action: str) -> str:
    return {
        "open_long": "开多",
        "open_short": "开空",
        "close_long": "平多",
        "close_short": "平空",
    }.get(action, action)


def build_trade_row(*, signal_time: str, symbol: str, action: str, payload: dict, realized_pnl: float) -> dict:
    qty = float(payload.get("qty", 1.0))
    base_asset = symbol.replace("USDT", "")
    price = float(payload.get("price", 0.0))
    return {
        "time": signal_time,
        "contract": f"{symbol} 永续",
        "direction": translate_action_label(action),
        "price": price,
        "price_text": "--" if price <= 0 else str(price),
        "qty_text": f"{qty:.3f} {base_asset}",
        "fee_text": "--",
        "role": "dry-run",
        "realized_pnl_text": f"{realized_pnl:+.8f} USDT",
    }


def render_trade_history_row(row: dict) -> str:
    return " | ".join(
        [
            row["time"],
            row["contract"],
            row["direction"],
            row["price_text"],
            row["qty_text"],
            row["fee_text"],
            row["role"],
            row["realized_pnl_text"],
        ]
    )


def compute_realized_pnl_rows(rows):
    open_position = None
    result = []

    for signal_time, symbol, action, payload in rows:
        payload = payload or {}
        price = float(payload.get("price", 0.0))
        qty = float(payload.get("qty", 1.0))
        realized_pnl = 0.0

        if action == "open_long" and price > 0:
            open_position = {"side": "long", "price": price, "qty": qty}
        elif action == "open_short" and price > 0:
            open_position = {"side": "short", "price": price, "qty": qty}
        elif action == "close_long" and price > 0 and open_position and open_position["side"] == "long":
            realized_pnl = (price - open_position["price"]) * open_position["qty"]
            open_position = None
        elif action == "close_short" and price > 0 and open_position and open_position["side"] == "short":
            realized_pnl = (open_position["price"] - price) * open_position["qty"]
            open_position = None

        result.append(
            build_trade_row(
                signal_time=signal_time,
                symbol=symbol,
                action=action,
                payload=payload,
                realized_pnl=realized_pnl,
            )
        )

    return result


def main() -> None:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT signal_time, symbol, action, payload_json
                FROM signal_events
                WHERE status = 'execute'
                ORDER BY signal_time DESC, id DESC
                LIMIT 20
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    normalized_rows = [
        (
            signal_time.isoformat() if hasattr(signal_time, "isoformat") else str(signal_time),
            symbol,
            action,
            payload or {},
        )
        for signal_time, symbol, action, payload in reversed(rows)
    ]

    for row in reversed(compute_realized_pnl_rows(normalized_rows)):
        print(render_trade_history_row(row))


if __name__ == "__main__":
    main()
