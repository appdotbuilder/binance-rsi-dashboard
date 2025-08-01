from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


# Enums for better type safety
class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DISMISSED = "dismissed"


class AlertCondition(str, Enum):
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    CUSTOM = "custom"


# Persistent models (stored in database)
class CoinPair(SQLModel, table=True):
    """Represents a trading pair from Binance Futures market"""

    __tablename__ = "coin_pairs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(unique=True, max_length=50, index=True)  # e.g., "BTCUSDT"
    base_asset: str = Field(max_length=20)  # e.g., "BTC"
    quote_asset: str = Field(max_length=20)  # e.g., "USDT"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    rsi_data: List["RSIData"] = Relationship(back_populates="coin_pair")
    user_preferences: List["UserCoinPreference"] = Relationship(back_populates="coin_pair")
    notifications: List["RSINotification"] = Relationship(back_populates="coin_pair")


class RSIData(SQLModel, table=True):
    """Stores RSI indicator data for each coin pair"""

    __tablename__ = "rsi_data"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    coin_pair_id: int = Field(foreign_key="coin_pairs.id", index=True)
    rsi_value: Decimal = Field(decimal_places=4, max_digits=8)  # RSI value (0-100)
    price: Decimal = Field(decimal_places=8, max_digits=20)  # Current price
    volume: Decimal = Field(decimal_places=8, max_digits=20, default=Decimal("0"))  # Trading volume
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Technical analysis metadata
    period: int = Field(default=14)  # RSI calculation period

    # Relationships
    coin_pair: CoinPair = Relationship(back_populates="rsi_data")


class User(SQLModel, table=True):
    """User accounts for personalized dashboard experience"""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, max_length=50)
    email: str = Field(unique=True, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    coin_preferences: List["UserCoinPreference"] = Relationship(back_populates="user")
    alert_settings: List["AlertSetting"] = Relationship(back_populates="user")
    notifications: List["RSINotification"] = Relationship(back_populates="user")


class UserCoinPreference(SQLModel, table=True):
    """Tracks which coin pairs a user wants to monitor"""

    __tablename__ = "user_coin_preferences"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    coin_pair_id: int = Field(foreign_key="coin_pairs.id", index=True)
    is_selected: bool = Field(default=True)
    display_order: int = Field(default=0)  # For custom ordering
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="coin_preferences")
    coin_pair: CoinPair = Relationship(back_populates="user_preferences")


class AlertSetting(SQLModel, table=True):
    """User-defined alert thresholds for RSI notifications"""

    __tablename__ = "alert_settings"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)  # User-friendly name for the alert
    condition: AlertCondition = Field(index=True)

    # RSI thresholds
    overbought_threshold: Decimal = Field(decimal_places=2, max_digits=5, default=Decimal("70.00"))
    oversold_threshold: Decimal = Field(decimal_places=2, max_digits=5, default=Decimal("30.00"))

    # Custom threshold for flexible alerts
    custom_threshold: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=5)
    custom_operator: Optional[str] = Field(default=None, max_length=10)  # ">=", "<=", "==", etc.

    is_enabled: bool = Field(default=True)
    applies_to_all_pairs: bool = Field(default=True)  # If false, specific pairs in coin_pair_filters
    coin_pair_filters: List[str] = Field(default=[], sa_column=Column(JSON))  # Specific symbols to monitor

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="alert_settings")
    notifications: List["RSINotification"] = Relationship(back_populates="alert_setting")


class RSINotification(SQLModel, table=True):
    """Generated notifications based on alert settings"""

    __tablename__ = "rsi_notifications"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    coin_pair_id: int = Field(foreign_key="coin_pairs.id", index=True)
    alert_setting_id: int = Field(foreign_key="alert_settings.id", index=True)

    # Notification details
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    rsi_value: Decimal = Field(decimal_places=4, max_digits=8)
    price_at_alert: Decimal = Field(decimal_places=8, max_digits=20)

    status: NotificationStatus = Field(default=NotificationStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    sent_at: Optional[datetime] = Field(default=None)
    dismissed_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: User = Relationship(back_populates="notifications")
    coin_pair: CoinPair = Relationship(back_populates="notifications")
    alert_setting: AlertSetting = Relationship(back_populates="notifications")


class DashboardConfig(SQLModel, table=True):
    """Global dashboard configuration settings"""

    __tablename__ = "dashboard_config"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    refresh_interval: int = Field(default=5)  # Seconds
    default_rsi_period: int = Field(default=14)
    max_historical_records: int = Field(default=1000)  # Per coin pair

    # Display settings
    display_settings: Dict[str, Any] = Field(
        default={"show_volume": True, "show_price": True, "show_timestamp": True, "theme": "light", "grid_columns": 4},
        sa_column=Column(JSON),
    )

    # Binance API settings
    api_settings: Dict[str, Any] = Field(
        default={
            "base_url": "https://fapi.binance.com",
            "rate_limit": 1200,  # requests per minute
            "timeout": 10,
        },
        sa_column=Column(JSON),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Non-persistent schemas (for validation, forms, API requests/responses)
class CoinPairCreate(SQLModel, table=False):
    symbol: str = Field(max_length=50)
    base_asset: str = Field(max_length=20)
    quote_asset: str = Field(max_length=20)
    is_active: bool = Field(default=True)


class CoinPairUpdate(SQLModel, table=False):
    symbol: Optional[str] = Field(default=None, max_length=50)
    base_asset: Optional[str] = Field(default=None, max_length=20)
    quote_asset: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = Field(default=None)


class RSIDataCreate(SQLModel, table=False):
    coin_pair_id: int
    rsi_value: Decimal
    price: Decimal
    volume: Decimal = Field(default=Decimal("0"))
    period: int = Field(default=14)


class UserCreate(SQLModel, table=False):
    username: str = Field(max_length=50)
    email: str = Field(max_length=255)


class UserUpdate(SQLModel, table=False):
    username: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = Field(default=None)


class AlertSettingCreate(SQLModel, table=False):
    user_id: int
    name: str = Field(max_length=100)
    condition: AlertCondition
    overbought_threshold: Decimal = Field(default=Decimal("70.00"), decimal_places=2, max_digits=5)
    oversold_threshold: Decimal = Field(default=Decimal("30.00"), decimal_places=2, max_digits=5)
    custom_threshold: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=5)
    custom_operator: Optional[str] = Field(default=None, max_length=10)
    applies_to_all_pairs: bool = Field(default=True)
    coin_pair_filters: List[str] = Field(default=[])


class AlertSettingUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    condition: Optional[AlertCondition] = Field(default=None)
    overbought_threshold: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=5)
    oversold_threshold: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=5)
    custom_threshold: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=5)
    custom_operator: Optional[str] = Field(default=None, max_length=10)
    is_enabled: Optional[bool] = Field(default=None)
    applies_to_all_pairs: Optional[bool] = Field(default=None)
    coin_pair_filters: Optional[List[str]] = Field(default=None)


class UserCoinPreferenceCreate(SQLModel, table=False):
    user_id: int
    coin_pair_id: int
    is_selected: bool = Field(default=True)
    display_order: int = Field(default=0)


class UserCoinPreferenceUpdate(SQLModel, table=False):
    is_selected: Optional[bool] = Field(default=None)
    display_order: Optional[int] = Field(default=None)


class NotificationCreate(SQLModel, table=False):
    user_id: int
    coin_pair_id: int
    alert_setting_id: int
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    rsi_value: Decimal
    price_at_alert: Decimal


class DashboardConfigUpdate(SQLModel, table=False):
    refresh_interval: Optional[int] = Field(default=None)
    default_rsi_period: Optional[int] = Field(default=None)
    max_historical_records: Optional[int] = Field(default=None)
    display_settings: Optional[Dict[str, Any]] = Field(default=None)
    api_settings: Optional[Dict[str, Any]] = Field(default=None)


# Response schemas for API endpoints
class RSIDataResponse(SQLModel, table=False):
    id: int
    symbol: str
    rsi_value: str  # Decimal serialized as string
    price: str  # Decimal serialized as string
    volume: str  # Decimal serialized as string
    timestamp: str  # ISO format datetime
    period: int


class CoinPairResponse(SQLModel, table=False):
    id: int
    symbol: str
    base_asset: str
    quote_asset: str
    is_active: bool
    created_at: str  # ISO format datetime
    latest_rsi: Optional[str] = Field(default=None)  # Latest RSI value as string


class NotificationResponse(SQLModel, table=False):
    id: int
    title: str
    message: str
    symbol: str
    rsi_value: str  # Decimal as string
    price_at_alert: str  # Decimal as string
    status: NotificationStatus
    created_at: str  # ISO format datetime
