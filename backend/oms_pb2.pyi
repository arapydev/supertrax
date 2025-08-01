from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TradeRequest(_message.Message):
    __slots__ = ("instrument", "side", "volume", "stop_loss", "take_profit")
    INSTRUMENT_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    STOP_LOSS_FIELD_NUMBER: _ClassVar[int]
    TAKE_PROFIT_FIELD_NUMBER: _ClassVar[int]
    instrument: str
    side: str
    volume: float
    stop_loss: float
    take_profit: float
    def __init__(self, instrument: _Optional[str] = ..., side: _Optional[str] = ..., volume: _Optional[float] = ..., stop_loss: _Optional[float] = ..., take_profit: _Optional[float] = ...) -> None: ...

class TradeResponse(_message.Message):
    __slots__ = ("success", "order_id", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    order_id: str
    message: str
    def __init__(self, success: bool = ..., order_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
