# main.py - Versión Final 1.0 con Logging

import asyncio
import MetaTrader5 as mt5
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import json
import os
import logging # Importamos la librería de logging

app = FastAPI()

# --- NUEVO: CONFIGURACIÓN DEL LOGGING ---
# Configuramos el logger para que escriba en un archivo.
logging.basicConfig(
    level=logging.INFO, # Nivel mínimo de mensajes a registrar
    format='%(asctime)s - %(levelname)s - %(message)s', # Formato: Fecha, Nivel, Mensaje
    filename='trading_log.log', # Nombre del archivo
    filemode='a' # 'a' para añadir al archivo, 'w' para sobreescribir en cada inicio
)
# Creamos un logger específico para nuestra aplicación
logger = logging.getLogger(__name__)
# --- FIN DE LA CONFIGURACIÓN DEL LOGGING ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

CONFIG_FILE = "trading_config.json"
instrument_states: Dict[str, Dict] = {}

def save_config():
    with open(CONFIG_FILE, 'w') as f: json.dump(instrument_states, f, indent=4)
    logger.info("Configuración guardada.")

def load_config():
    global instrument_states
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: instrument_states = json.load(f)
        logger.info(f"Configuración cargada para: {list(instrument_states.keys())}")
    else:
        logger.warning("No se encontró archivo de configuración, creando uno nuevo.")
        instrument_states = {"EURUSD": {"auto_trading": False, "lot_size": 0.01, "sl_pips": 10, "tp_pips": 30, "strategy": "FractalBreakout"}}
        save_config()

@app.on_event("startup")
async def startup_event():
    load_config()
    if not mt5.initialize():
        logger.error("Fallo al inicializar MetaTrader 5.")
    else:
        logger.info("Conexión con MetaTrader 5 establecida.")

@app.on_event("shutdown")
async def shutdown_event():
    mt5.shutdown()
    logger.info("Conexión con MetaTrader 5 cerrada.")

def get_broker_symbol(instrument: str) -> str | None:
    symbols = mt5.symbols_get()
    if symbols is None: return None
    for s in symbols:
        if s.name == instrument: return s.name
    for s in symbols:
        if s.name.startswith(instrument): return s.name
    return None

class InstrumentRequest(BaseModel): instrument: str
@app.post("/api/add_instrument")
async def add_instrument(request: InstrumentRequest):
    instrument_name = request.instrument.upper()
    if instrument_name in instrument_states:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="El instrumento ya existe.")
    broker_symbol = get_broker_symbol(instrument_name)
    if not broker_symbol:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Símbolo '{instrument_name}' no encontrado en el bróker.")
    if not mt5.symbol_info_tick(broker_symbol):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"No se pueden obtener datos para '{broker_symbol}'. Asegúrate de que está en tu Observación de Mercado.")
    instrument_states[instrument_name] = {"auto_trading": False, "lot_size": 0.01, "sl_pips": 10, "tp_pips": 30, "strategy": "FractalBreakout"}
    save_config()
    logger.info(f"Instrumento añadido: {instrument_name}")
    return {"message": f"Instrumento {instrument_name} añadido."}

@app.post("/api/remove_instrument")
async def remove_instrument(request: InstrumentRequest):
    instrument_name = request.instrument.upper()
    if instrument_name not in instrument_states:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="El instrumento no se encontró.")
    del instrument_states[instrument_name]
    save_config()
    logger.info(f"Instrumento eliminado: {instrument_name}")
    return {"message": f"Instrumento {instrument_name} eliminado."}

class TradingMode(BaseModel): instrument: str; enabled: bool
class LotSize(BaseModel): instrument: str; volume: float
class SlTpConfig(BaseModel): instrument: str; sl_pips: int; tp_pips: int
@app.post("/api/trading_mode")
async def set_trading_mode(mode: TradingMode):
    if mode.instrument in instrument_states:
        instrument_states[mode.instrument]["auto_trading"] = mode.enabled
        save_config()
        status_text = "ACTIVADO" if mode.enabled else "DESACTIVADO"
        logger.info(f"Modo auto para {mode.instrument} {status_text}.")
        return {"message": f"Modo auto para {mode.instrument} ahora está {status_text}"}
    else: from fastapi import HTTPException; raise HTTPException(status_code=404, detail="Instrumento no encontrado.")
@app.post("/api/lot_size")
async def set_lot_size(lot: LotSize):
    if lot.instrument in instrument_states:
        if 0.01 <= lot.volume <= 100.0:
            instrument_states[lot.instrument]["lot_size"] = lot.volume
            save_config()
            logger.info(f"Lotaje para {lot.instrument} actualizado a: {lot.volume}")
            return {"message": f"Lotaje para {lot.instrument} actualizado."}
        else: from fastapi import HTTPException; raise HTTPException(status_code=400, detail="Lotaje inválido.")
    else: from fastapi import HTTPException; raise HTTPException(status_code=404, detail="Instrumento no encontrado.")
@app.post("/api/sl_tp")
async def set_sl_tp(config: SlTpConfig):
    if config.instrument in instrument_states:
        instrument_states[config.instrument]["sl_pips"] = config.sl_pips
        instrument_states[config.instrument]["tp_pips"] = config.tp_pips
        save_config()
        logger.info(f"SL/TP para {config.instrument} actualizado a: SL={config.sl_pips}, TP={config.tp_pips}")
        return {"message": f"SL/TP para {config.instrument} actualizado."}
    else: from fastapi import HTTPException; raise HTTPException(status_code=404, detail="Instrumento no encontrado.")
class ManualTrade(BaseModel): instrument: str; side: str; volume: float
@app.post("/api/manual_trade")
async def execute_manual_trade(trade: ManualTrade):
    state = instrument_states.get(trade.instrument, {})
    sl_pips = state.get("sl_pips", 10)
    tp_pips = state.get("tp_pips", 30)
    result = await asyncio.to_thread(send_mt5_order, trade.instrument, trade.side, trade.volume, sl_pips, tp_pips)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE: return {"message": f"Orden manual {trade.side} ejecutada."}
    else: from fastapi import HTTPException; raise HTTPException(status_code=500, detail="Fallo al ejecutar la orden manual.")
class BreakevenRequest(BaseModel): instrument: str; extra_pips: int = 1
@app.post("/api/breakeven")
async def move_to_breakeven(request: BreakevenRequest):
    result = await asyncio.to_thread(set_position_to_breakeven, request.instrument, request.extra_pips)
    if result["success"]: return {"message": result["message"]}
    else: from fastapi import HTTPException; raise HTTPException(status_code=400, detail=result["message"])
class TrailRequest(BaseModel): instrument: str; pips_to_add: int = 1
@app.post("/api/trail_stop")
async def trail_sl(request: TrailRequest):
    result = await asyncio.to_thread(trail_stop_loss, request.instrument, request.pips_to_add)
    if result["success"]: return {"message": result["message"]}
    else: from fastapi import HTTPException; raise HTTPException(status_code=400, detail=result["message"])
class FlattenRequest(BaseModel): instrument: str
@app.post("/api/flatten")
async def flatten_positions(request: FlattenRequest):
    success = await asyncio.to_thread(close_all_positions, request.instrument)
    if success: return {"message": f"Posiciones para {request.instrument} cerradas."}
    else: from fastapi import HTTPException; raise HTTPException(status_code=500, detail="Fallo al cerrar posiciones.")

def has_open_position(instrument: str) -> bool:
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return False
    positions = mt5.positions_get(symbol=broker_symbol)
    return not (positions is None or len(positions) == 0)

def send_mt5_order(instrument: str, signal: str, volume: float, sl_pips: int, tp_pips: int):
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol:
        logger.error(f"Símbolo para {instrument} no encontrado en el bróker.")
        return
    logger.info(f"INTENTANDO EJECUTAR ORDEN: {signal} {volume} lotes de {broker_symbol} con SL={sl_pips}, TP={tp_pips}")
    order_type_map = {"BUY": mt5.ORDER_TYPE_BUY, "SELL": mt5.ORDER_TYPE_SELL}
    order_type = order_type_map[signal]
    symbol_info = mt5.symbol_info(broker_symbol)
    price = mt5.symbol_info_tick(broker_symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(broker_symbol).bid
    point = symbol_info.point
    pip_multiplier = 10 if symbol_info.digits in [5, 3] else 1
    sl_points, tp_points = sl_pips * pip_multiplier, tp_pips * pip_multiplier
    sl = price - sl_points * point if order_type == mt5.ORDER_TYPE_BUY else price + sl_points * point
    tp = price + tp_points * point if order_type == mt5.ORDER_TYPE_BUY else price - tp_points * point
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": broker_symbol, "volume": volume, "type": order_type, "price": price, "sl": round(sl, symbol_info.digits), "tp": round(tp, symbol_info.digits), "deviation": 20, "magic": 234000, "comment": "Orden enviada por Python", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Fallo al enviar la orden: retcode={result.retcode}, comentario={result.comment}")
    else:
        logger.info(f"¡ORDEN EJECUTADA CON ÉXITO! Ticket: {result.order}")
    return result

def close_all_positions(instrument: str) -> bool:
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return False
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions: return True
    logger.info(f"Cerrando {len(positions)} posicion(es) para {instrument}...")
    for position in positions:
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(broker_symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(broker_symbol).ask
        close_request = {"action": mt5.TRADE_ACTION_DEAL, "position": position.ticket, "symbol": broker_symbol, "volume": position.volume, "type": order_type, "price": price, "deviation": 20, "magic": 234000, "comment": "Cierre FLATTEN", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
        result = mt5.order_send(close_request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Fallo al cerrar la posición #{position.ticket}: {result.comment}")
            return False
    logger.info(f"Todas las posiciones para {instrument} han sido cerradas.")
    return True

def set_position_to_breakeven(instrument: str, extra_pips: int):
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return {"success": False, "message": "Símbolo no encontrado."}
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions: return {"success": False, "message": "No hay posición abierta."}
    position = positions[0]
    symbol_info = mt5.symbol_info(broker_symbol)
    point = symbol_info.point
    pip_multiplier = 10 if symbol_info.digits in [5, 3] else 1
    extra_points = extra_pips * pip_multiplier * point
    if position.type == mt5.ORDER_TYPE_BUY:
        new_sl = position.price_open + extra_points
        current_price = mt5.symbol_info_tick(broker_symbol).bid
        if current_price <= new_sl: return {"success": False, "message": "El precio está demasiado cerca."}
    else:
        new_sl = position.price_open - extra_points
        current_price = mt5.symbol_info_tick(broker_symbol).ask
        if current_price >= new_sl: return {"success": False, "message": "El precio está demasiado cerca."}
    modify_request = {"action": mt5.TRADE_ACTION_SLTP, "position": position.ticket, "sl": new_sl, "tp": position.tp}
    result = mt5.order_send(modify_request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Posición #{position.ticket} movida a BE +{extra_pips} pips.")
        return {"success": True, "message": f"Posición movida a BE +{extra_pips} pips."}
    else:
        logger.error(f"Fallo al mover a BE la posición #{position.ticket}: {result.comment}")
        return {"success": False, "message": f"Fallo al mover a BE: {result.comment}"}

def trail_stop_loss(instrument: str, pips_to_add: int):
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return {"success": False, "message": "Símbolo no encontrado."}
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions: return {"success": False, "message": "No hay posición abierta."}
    position = positions[0]
    if position.sl == 0: return {"success": False, "message": "La posición no tiene SL."}
    symbol_info = mt5.symbol_info(broker_symbol)
    point = symbol_info.point
    pip_multiplier = 10 if symbol_info.digits in [5, 3] else 1
    points_to_add = pips_to_add * pip_multiplier * point
    if position.type == mt5.ORDER_TYPE_BUY:
        new_sl = position.sl + points_to_add
        current_price = mt5.symbol_info_tick(broker_symbol).bid
        if current_price <= new_sl: return {"success": False, "message": "No se puede mover el SL."}
    else:
        new_sl = position.sl - points_to_add
        current_price = mt5.symbol_info_tick(broker_symbol).ask
        if current_price >= new_sl: return {"success": False, "message": "No se puede mover el SL."}
    modify_request = {"action": mt5.TRADE_ACTION_SLTP, "position": position.ticket, "sl": new_sl, "tp": position.tp}
    result = mt5.order_send(modify_request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"SL de la posición #{position.ticket} movido +{pips_to_add} pips.")
        return {"success": True, "message": f"SL movido +{pips_to_add} pips."}
    else:
        logger.error(f"Fallo al mover SL de la posición #{position.ticket}: {result.comment}")
        return {"success": False, "message": f"Fallo al mover SL: {result.comment}"}

def find_latest_fractals(df: pd.DataFrame):
    latest_up_fractal, latest_down_fractal = None, None
    for i in range(len(df) - 3, 2, -1):
        is_up = (df['high'][i]>df['high'][i-1] and df['high'][i]>df['high'][i-2] and df['high'][i]>df['high'][i+1] and df['high'][i]>df['high'][i+2])
        if is_up and latest_up_fractal is None: latest_up_fractal = df['high'][i]
        is_down = (df['low'][i]<df['low'][i-1] and df['low'][i]<df['low'][i-2] and df['low'][i]<df['low'][i+1] and df['low'][i]<df['low'][i+2])
        if is_down and latest_down_fractal is None: latest_down_fractal = df['low'][i]
        if latest_up_fractal and latest_down_fractal: break
    return latest_up_fractal, latest_down_fractal

last_fractals = {}
async def update_fractals_and_generate_signal(instrument: str, current_price: float):
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return None, None, None
    rates = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None or len(rates) < 10: return None, None, None
    df = pd.DataFrame(rates)
    up_fractal, down_fractal = find_latest_fractals(df)
    if instrument not in last_fractals: last_fractals[instrument] = {"up": None, "down": None}
    if up_fractal: last_fractals[instrument]["up"] = up_fractal
    if down_fractal: last_fractals[instrument]["down"] = down_fractal
    last_up, last_down = last_fractals[instrument]["up"], last_fractals[instrument]["down"]
    new_signal = None
    state = instrument_states.get(instrument)
    if state and not has_open_position(instrument):
        if last_up and current_price > last_up:
            new_signal = "BUY"
            if state["auto_trading"]: asyncio.create_task(asyncio.to_thread(send_mt5_order, instrument, new_signal, state["lot_size"], state["sl_pips"], state["tp_pips"]))
        elif last_down and current_price < last_down:
            new_signal = "SELL"
            if state["auto_trading"]: asyncio.create_task(asyncio.to_thread(send_mt5_order, instrument, new_signal, state["lot_size"], state["sl_pips"], state["tp_pips"]))
    return new_signal, last_up, last_down

def get_position_data(instrument: str) -> Dict[str, Any] | None:
    broker_symbol = get_broker_symbol(instrument)
    if not broker_symbol: return None
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions: return None
    pos = positions[0]
    return {"ticket": pos.ticket, "type": "BUY" if pos.type == 0 else "SELL", "volume": pos.volume, "price_open": pos.price_open, "sl": pos.sl, "tp": pos.tp, "profit": pos.profit}

@app.websocket("/ws/market_data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            current_instruments = list(instrument_states.keys())
            for instrument in current_instruments:
                broker_symbol = get_broker_symbol(instrument)
                if broker_symbol: mt5.symbol_select(broker_symbol, True)
            all_data = {}
            account_info = mt5.account_info()
            for instrument in current_instruments:
                broker_symbol = get_broker_symbol(instrument)
                if not broker_symbol: continue
                latest_tick = mt5.symbol_info_tick(broker_symbol)
                if latest_tick:
                    current_price = (latest_tick.bid + latest_tick.ask) / 2
                    signal, last_up, last_down = await update_fractals_and_generate_signal(instrument, current_price)
                    state = instrument_states.get(instrument, {})
                    all_data[instrument] = {"bid": latest_tick.bid, "ask": latest_tick.ask, "signal": signal, "last_up_fractal": last_up, "last_down_fractal": last_down, "position": get_position_data(instrument), "auto_trading": state.get("auto_trading"), "lot_size": state.get("lot_size"), "sl_pips": state.get("sl_pips"), "tp_pips": state.get("tp_pips")}
            if account_info:
                all_data["account"] = {"balance": account_info.balance, "equity": account_info.equity, "profit": account_info.profit}
            await websocket.send_json(all_data)
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error en WebSocket: {repr(e)}")
    finally:
        all_symbols = mt5.symbols_get()
        if all_symbols:
            for symbol in all_symbols: mt5.symbol_select(symbol.name, False)
        logger.info("Suscripciones canceladas.")