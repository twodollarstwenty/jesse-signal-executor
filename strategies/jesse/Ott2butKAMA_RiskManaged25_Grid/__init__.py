import types

try:
    import talib
except ModuleNotFoundError:  # pragma: no cover - test-only import fallback
    talib = types.SimpleNamespace(RSI=lambda *args, **kwargs: None)

try:
    from jesse import utils
    from jesse.strategies import Strategy, cached
except ModuleNotFoundError:  # pragma: no cover - test-only import fallback
    utils = types.SimpleNamespace(
        size_to_qty=lambda *args, **kwargs: None,
        crossed=lambda *args, **kwargs: None,
    )

    class Strategy:
        pass

    def cached(func):
        return func

try:
    import custom_indicators_ottkama as cta
except ModuleNotFoundError:  # pragma: no cover - test-only import fallback
    cta = types.SimpleNamespace(ott=lambda *args, **kwargs: None)

try:
    from apps.signal_service.jesse_bridge.emitter import emit_signal
except ModuleNotFoundError:  # pragma: no cover - test-only import fallback
    def emit_signal(**kwargs):
        return None


def compute_layer_sizes(total_qty):
    return [total_qty * 0.4, total_qty * 0.3, total_qty * 0.3]


def compute_long_layer_prices(entry_price):
    return [entry_price, entry_price * 0.996, entry_price * 0.992]


def compute_short_layer_prices(entry_price):
    return [entry_price, entry_price * 1.004, entry_price * 1.008]


# Old ott2 but uses KAMA instead of VAR.
# Stoploss is still same.


class Ott2butKAMA_RiskManaged25_Grid(Strategy):
    def __init__(self):
        super().__init__()
        self.trade_ts = None

    def hyperparameters(self):
        return [
            {'name': 'ott_len', 'type': int, 'min': 2, 'max': 75, 'default': 36},
            {'name': 'ott_percent', 'type': int, 'min': 100, 'max': 800, 'default': 540},
            {'name': 'stop_loss', 'type': int, 'min': 50, 'max': 400, 'default': 122},
            {'name': 'risk_reward', 'type': int, 'min': 10, 'max': 80, 'default': 40},
            {'name': 'chop_rsi_len', 'type': int, 'min': 2, 'max': 75, 'default': 17},
            {'name': 'chop_bandwidth', 'type': int, 'min': 10, 'max': 350, 'default': 144},
            {'name': 'risk_per_trade', 'type': int, 'min': 1, 'max': 50, 'default': 25},
        ]

    @property
    @cached
    def ott_len(self):
        return self.hp['ott_len']

    @property
    @cached
    def ott_percent(self):
        return self.hp['ott_percent'] / 100

    @property
    @cached
    def stop(self):
        return self.hp['stop_loss'] / 10000

    @property
    @cached
    def RRR(self):
        return self.hp['risk_reward'] / 10

    @property
    @cached
    def risk_fraction(self):
        return self.hp['risk_per_trade'] / 1000

    @property
    @cached
    def ott(self):
        return cta.ott(self.candles[-960:, 2], self.ott_len, self.ott_percent, ma_type='kama', sequential=True)

    @property
    @cached
    def chop(self):
        return talib.RSI(self.candles[-960:, 2], self.hp['chop_rsi_len'])

    @property
    @cached
    def chop_upper_band(self):
        return 40 + (self.hp['chop_bandwidth'] / 10)

    @property
    @cached
    def chop_lower_band(self):
        return 60 - (self.hp['chop_bandwidth'] / 10)

    def should_long(self) -> bool:
        return self.cross_up and self.chop[-1] > self.chop_upper_band

    def should_short(self) -> bool:
        return self.cross_down and self.chop[-1] < self.chop_lower_band

    def compute_risk_based_qty(self, *, stop_price: float, side: str = "long") -> float:
        if side == "short":
            stop_distance = stop_price - self.price
        else:
            stop_distance = self.price - stop_price
        if stop_distance <= 0:
            return 0
        risk_amount = self.balance * self.risk_fraction
        return risk_amount / stop_distance

    @property
    @cached
    def pos_size(self):
        estimated_stop = self.ott.ott[-1] - (self.ott.ott[-1] * self.stop)
        return self.compute_risk_based_qty(stop_price=estimated_stop, side="long")

    @property
    def long_layer_sizes(self):
        return compute_layer_sizes(self.pos_size)

    @property
    def short_layer_sizes(self):
        return compute_layer_sizes(self.compute_risk_based_qty(
            stop_price=self.ott.ott[-1] + (self.ott.ott[-1] * self.stop),
            side="short",
        ))

    @property
    def long_layer_prices(self):
        return compute_long_layer_prices(self.price)

    @property
    def short_layer_prices(self):
        return compute_short_layer_prices(self.price)

    def go_long(self):
        emit_signal(
            strategy="Ott2butKAMA_RiskManaged25_Grid",
            symbol=self.symbol.replace('-', ''),
            timeframe=self.timeframe,
            candle_timestamp=int(self.current_candle[0]),
            action="open_long",
            payload={"source": "jesse", "price": float(self.price)},
        )
        self.buy = self.long_layer_sizes[0], self.long_layer_prices[0]

    def go_short(self):
        emit_signal(
            strategy="Ott2butKAMA_RiskManaged25_Grid",
            symbol=self.symbol.replace('-', ''),
            timeframe=self.timeframe,
            candle_timestamp=int(self.current_candle[0]),
            action="open_short",
            payload={"source": "jesse", "price": float(self.price)},
        )
        self.sell = self.short_layer_sizes[0], self.short_layer_prices[0]

    def on_open_position(self, order):
        if self.is_long:
            sl = self.ott.ott[-1] - (self.ott.ott[-1] * self.stop)
            self.stop_loss = self.position.qty, sl
            tp = self.position.entry_price + (self.position.entry_price * (self.stop * self.RRR))
            self.take_profit = self.position.qty, tp

        if self.is_short:
            sl = self.ott.ott[-1] + (self.ott.ott[-1] * self.stop)
            self.stop_loss = self.position.qty, sl
            tp = self.position.entry_price - (self.position.entry_price * (self.stop * self.RRR))
            self.take_profit = self.position.qty, tp

    @property
    @cached
    def cross_up(self):
        return utils.crossed(self.ott.mavg, self.ott.ott, direction='above', sequential=False)

    @property
    @cached
    def cross_down(self):
        return utils.crossed(self.ott.mavg, self.ott.ott, direction='below', sequential=False)

    def update_position(self):
        if self.is_long and self.cross_down:
            emit_signal(
                strategy="Ott2butKAMA_RiskManaged25_Grid",
                symbol=self.symbol.replace('-', ''),
                timeframe=self.timeframe,
                candle_timestamp=int(self.current_candle[0]),
                action="close_long",
                payload={"source": "jesse", "price": float(self.price), "position_side": "long"},
            )
            self.liquidate()
        if self.is_short and self.cross_up:
            emit_signal(
                strategy="Ott2butKAMA_RiskManaged25_Grid",
                symbol=self.symbol.replace('-', ''),
                timeframe=self.timeframe,
                candle_timestamp=int(self.current_candle[0]),
                action="close_short",
                payload={"source": "jesse", "price": float(self.price), "position_side": "short"},
            )
            self.liquidate()

    def should_cancel(self) -> bool:
        return True
