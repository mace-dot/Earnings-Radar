"""Non-secret configuration and presence-only connection status."""
import os
from dataclasses import dataclass, field
from earnings_radar.validation import ticker

@dataclass
class Settings:
    watchlist: tuple[str,...] = field(default_factory=lambda: tuple(ticker(t) for t in os.getenv('RADAR_WATCHLIST','AAPL,MSFT,NVDA').split(',') if t.strip()))
    sec_user_agent: str = field(default_factory=lambda: os.getenv('SEC_USER_AGENT',''))
    poll_seconds: int = 300
    max_backfill_age_seconds: int = 7200
    max_attempts: int = 5
    model_enabled: bool = field(default_factory=lambda: os.getenv('RADAR_MODEL_ENABLED','false').lower()=='true')
    model: str = field(default_factory=lambda: os.getenv('RADAR_MODEL','claude-sonnet-4-5'))
    model_daily_budget: float = field(default_factory=lambda: float(os.getenv('RADAR_MODEL_DAILY_BUDGET_USD','1')))
    telegram_enabled: bool = field(default_factory=lambda: os.getenv('RADAR_TELEGRAM_ENABLED','false').lower()=='true')
    telegram_verified: bool = field(default_factory=lambda: os.getenv('RADAR_TELEGRAM_DESTINATION_VERIFIED','false').lower()=='true')
    notify_severity: str = field(default_factory=lambda: os.getenv('RADAR_NOTIFY_SEVERITY','high'))
    quiet_start: int = field(default_factory=lambda: int(os.getenv('RADAR_QUIET_START','22')))
    quiet_end: int = field(default_factory=lambda: int(os.getenv('RADAR_QUIET_END','8')))
    urgent_exception: bool = field(default_factory=lambda: os.getenv('RADAR_URGENT_QUIET_EXCEPTION','false').lower()=='true')
    cooldown_seconds: int = 900

    def __post_init__(self):
        if not 1 <= len(self.watchlist) <= 20:
            raise ValueError('watchlist must contain 1–20 tickers')
        if not 0 <= self.quiet_start <= 23 or not 0 <= self.quiet_end <= 23:
            raise ValueError('quiet hours must be 0–23')
        if self.model_daily_budget < 0:
            raise ValueError('budget must be nonnegative')

    @property
    def alpaca_available(self):
        return all(os.getenv(k) for k in ('ALPACA_API_KEY','ALPACA_API_SECRET'))
