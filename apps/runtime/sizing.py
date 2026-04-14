def _round_qty(value: float) -> float:
    return round(value, 8)


def compute_order_qty(*, capital_usdt: float, price: float, sizing: dict, signal_payload: dict) -> float:
    mode = sizing["mode"]
    if price <= 0:
        raise ValueError("price must be positive")

    if mode == "fixed_fraction":
        leverage = float(sizing.get("leverage", 1.0))
        position_fraction = float(sizing["position_fraction"])
        return _round_qty((capital_usdt * position_fraction * leverage) / price)

    if mode == "fixed_notional":
        return _round_qty(float(sizing["notional_usdt"]) / price)

    if mode == "risk_per_trade":
        stop_price = signal_payload.get("stop_price")
        if stop_price is None:
            raise ValueError("risk_per_trade sizing requires stop_price")
        stop_distance = abs(float(price) - float(stop_price))
        if stop_distance <= 0:
            raise ValueError("risk_per_trade sizing requires a positive stop distance")
        risk_fraction = sizing.get("risk_fraction")
        if risk_fraction is None:
            risk_bps = sizing.get("risk_bps")
            if risk_bps is None:
                raise ValueError("risk_per_trade sizing requires risk_fraction or risk_bps")
            risk_fraction = float(risk_bps) / 10000
        allowed_loss = capital_usdt * float(risk_fraction)
        return _round_qty(allowed_loss / stop_distance)

    raise ValueError(f"unsupported sizing mode: {mode}")
