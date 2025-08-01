// App.tsx - Versión con Gestión Dinámica de Instrumentos

import { useState, useEffect } from 'react';

// --- Interfaces (sin cambios) ---
interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error';
}
interface AccountData { balance: number; equity: number; profit: number; }
interface PositionData {
  ticket: number; type: 'BUY' | 'SELL'; volume: number;
  price_open: number; sl: number; tp: number; profit: number;
}
interface InstrumentData {
  bid: number; ask: number; signal: 'BUY' | 'SELL' | null;
  last_up_fractal: number | null; last_down_fractal: number | null;
  position: PositionData | null;
  auto_trading: boolean;
  lot_size: number;
  sl_pips: number;
  tp_pips: number;
}
interface WsData {
  account: AccountData;
  [instrument: string]: InstrumentData | AccountData;
}

// --- Componente InstrumentPanel (sin cambios) ---
interface InstrumentPanelProps {
  instrumentName: string;
  instrumentData: InstrumentData;
  addToast: (message: string, type: 'success' | 'error') => void;
}
function InstrumentPanel({ instrumentName, instrumentData, addToast }: InstrumentPanelProps) {
  const [isAutoTrading, setIsAutoTrading] = useState(instrumentData.auto_trading);
  const [lotSize, setLotSize] = useState(instrumentData.lot_size.toString());
  const [slPips, setSlPips] = useState(instrumentData.sl_pips.toString());
  const [tpPips, setTpPips] = useState(instrumentData.tp_pips.toString());
  const [isBusy, setIsBusy] = useState(false);
  const [lastSignal, setLastSignal] = useState<string | null>(null);

  useEffect(() => {
    setIsAutoTrading(instrumentData.auto_trading);
    setLotSize(instrumentData.lot_size.toString());
    setSlPips(instrumentData.sl_pips.toString());
    setTpPips(instrumentData.tp_pips.toString());
    if (instrumentData.signal) {
      setLastSignal(instrumentData.signal);
    }
  }, [instrumentData]);

  const handleToggleAutoTrading = async () => {
    const newStatus = !isAutoTrading;
    setIsAutoTrading(newStatus);
    try {
      await fetch('http://127.0.0.1:8000/api/trading_mode', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, enabled: newStatus }), });
    } catch (error) {
      addToast(`Error al cambiar modo para ${instrumentName}`, 'error');
      setIsAutoTrading(!newStatus);
    }
  };
  const handleLotSizeChange = async (newLotSize: string) => {
    setLotSize(newLotSize);
    const volume = parseFloat(newLotSize);
    if (!isNaN(volume) && volume > 0) {
      try {
        await fetch('http://127.0.0.1:8000/api/lot_size', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, volume: volume }), });
      } catch (error) { addToast(`Error al actualizar lotaje para ${instrumentName}`, 'error'); }
    }
  };
  const handleSlTpChange = async (sl: string, tp: string) => {
    setSlPips(sl);
    setTpPips(tp);
    const slNum = parseInt(sl, 10);
    const tpNum = parseInt(tp, 10);
    if (!isNaN(slNum) && !isNaN(tpNum) && slNum > 0 && tpNum > 0) {
      try {
        await fetch('http://127.0.0.1:8000/api/sl_tp', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, sl_pips: slNum, tp_pips: tpNum }), });
      } catch (error) { addToast(`Error al actualizar SL/TP para ${instrumentName}`, 'error'); }
    }
  };
  const handleFlatten = async () => {
    setIsBusy(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/flatten', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName }), });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); } else { addToast(result.message, 'success'); }
    } catch (error) { addToast('Error de red al cerrar posiciones.', 'error'); }
    finally { setIsBusy(false); }
  };
  const handleManualTrade = async (side: 'BUY' | 'SELL') => {
    setIsBusy(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/manual_trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, side: side, volume: parseFloat(lotSize) }), });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); } else { addToast(result.message, 'success'); }
    } catch (error) { addToast('Error de red en orden manual.', 'error'); }
    finally { setIsBusy(false); }
  };
  const handleBreakevenPlusOne = async () => {
    setIsBusy(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/breakeven', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, extra_pips: 1 }), });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); } else { addToast(result.message, 'success'); }
    } catch (error) { addToast('Error de red en BE+1.', 'error'); }
    finally { setIsBusy(false); }
  };
  const handleTrailStop = async () => {
    setIsBusy(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/trail_stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instrument: instrumentName, pips_to_add: 1 }), });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); } else { addToast(result.message, 'success'); }
    } catch (error) { addToast('Error de red en Trail SL.', 'error'); }
    finally { setIsBusy(false); }
  };
  const getProfitStyle = (profit: number) => { const color = profit >= 0 ? '#28a745' : '#dc3545'; return { color: color, fontWeight: 'bold' }; };

  return (
    <div style={{ display: 'flex', gap: '20px', padding: '20px' }}>
      <div style={{ flex: 1 }}>
        <h3>Datos de Mercado</h3>
        <div style={{ fontSize: '18px', textAlign: 'left', padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
          <p>BID: <span style={{ color: 'red', fontWeight: 'bold' }}>{instrumentData.bid.toFixed(5)}</span></p>
          <p>ASK: <span style={{ color: 'green', fontWeight: 'bold' }}>{instrumentData.ask.toFixed(5)}</span></p>
          <p>Fractal Sup: {instrumentData.last_up_fractal?.toFixed(5) || '...'}</p>
          <p>Fractal Inf: {instrumentData.last_down_fractal?.toFixed(5) || '...'}</p>
        </div>
        <h3 style={{ marginTop: '20px' }}>Última Señal Generada</h3>
        <div style={{ minHeight: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px', borderRadius: '5px', color: 'white', backgroundColor: lastSignal === 'BUY' ? '#28a745' : lastSignal === 'SELL' ? '#dc3545' : '#6c757d', fontSize: '18px', fontWeight: 'bold' }}>
          {lastSignal || '---'}
        </div>
        <h3 style={{ marginTop: '20px' }}>Posición Abierta</h3>
        {instrumentData.position ? (
          <div style={{ textAlign: 'left', padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
            <p><strong>Ticket:</strong> {instrumentData.position.ticket}</p>
            <p><strong>Tipo:</strong> <span style={{ color: instrumentData.position.type === 'BUY' ? 'blue' : 'orange' }}>{instrumentData.position.type}</span></p>
            <p><strong>Volumen:</strong> {instrumentData.position.volume}</p>
            <p><strong>Entrada:</strong> {instrumentData.position.price_open.toFixed(5)}</p>
            <p><strong>SL:</strong> {instrumentData.position.sl.toFixed(5)}</p>
            <p><strong>TP:</strong> {instrumentData.position.tp.toFixed(5)}</p>
            <p><strong>Profit:</strong> <span style={getProfitStyle(instrumentData.position.profit)}>{instrumentData.position.profit.toFixed(2)}</span></p>
          </div>
        ) : ( <p>No hay posiciones abiertas.</p> )}
      </div>
      <div style={{ flex: 1, borderLeft: '2px solid #f0f0f0', paddingLeft: '20px' }}>
        <h3>Panel de Control</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '15px', alignItems: 'center' }}>
          <span>Auto Trading</span>
          <label style={{ display: 'inline-flex', position: 'relative', height: '28px', width: '50px' }}>
            <input type="checkbox" checked={isAutoTrading} onChange={handleToggleAutoTrading} style={{ opacity: 0, width: 0, height: 0 }} />
            <span style={{ position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: isAutoTrading ? '#28a745' : '#ccc', transition: '.4s', borderRadius: '28px' }}></span>
            <span style={{ position: 'absolute', content: '""', height: '20px', width: '20px', left: '4px', bottom: '4px', backgroundColor: 'white', transition: '.4s', borderRadius: '50%', transform: isAutoTrading ? 'translateX(22px)' : 'translateX(0)' }}></span>
          </label>
          <label htmlFor={`lot-${instrumentName}`}>Lotaje:</label>
          <input id={`lot-${instrumentName}`} type="number" value={lotSize} onChange={(e) => handleLotSizeChange(e.target.value)} step="0.01" min="0.01" style={{ width: '80px', padding: '5px' }} />
          <label htmlFor={`sl-${instrumentName}`}>SL (pips):</label>
          <input id={`sl-${instrumentName}`} type="number" value={slPips} onChange={(e) => handleSlTpChange(e.target.value, tpPips)} step="1" min="1" style={{ width: '80px', padding: '5px' }} />
          <label htmlFor={`tp-${instrumentName}`}>TP (pips):</label>
          <input id={`tp-${instrumentName}`} type="number" value={tpPips} onChange={(e) => handleSlTpChange(slPips, e.target.value)} step="1" min="1" style={{ width: '80px', padding: '5px' }} />
        </div>
        <h4 style={{ marginTop: '20px' }}>Acciones Manuales</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
          <button onClick={() => handleManualTrade('BUY')} disabled={isBusy} style={{ backgroundColor: '#007bff', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>BUY</button>
          <button onClick={() => handleManualTrade('SELL')} disabled={isBusy} style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>SELL</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
          <button onClick={handleBreakevenPlusOne} disabled={isBusy || !instrumentData.position} style={{ backgroundColor: '#17a2b8', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer', opacity: instrumentData.position ? 1 : 0.5 }}>BE +1</button>
          <button onClick={handleTrailStop} disabled={isBusy || !instrumentData.position} style={{ backgroundColor: '#28a745', color: 'white', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer', opacity: instrumentData.position ? 1 : 0.5 }}>Trail SL +1</button>
        </div>
        <button onClick={handleFlatten} disabled={isBusy || !instrumentData.position} style={{ width: '100%', backgroundColor: '#ffc107', color: 'black', border: 'none', padding: '10px', borderRadius: '5px', cursor: 'pointer', opacity: instrumentData.position ? 1 : 0.5 }}>FLATTEN</button>
      </div>
    </div>
  );
}

// --- Componente Principal App (con Gestión de Instrumentos) ---
function App() {
  const [wsData, setWsData] = useState<WsData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState('Conectando...');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [activeTab, setActiveTab] = useState('');
  const [newInstrument, setNewInstrument] = useState('');

  const instrumentKeys = wsData ? Object.keys(wsData).filter(key => key !== 'account') : [];

  useEffect(() => {
    if (!activeTab && instrumentKeys.length > 0) {
      setActiveTab(instrumentKeys[0]);
    }
  }, [instrumentKeys, activeTab]);

  const addToast = (message: string, type: 'success' | 'error') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => { setToasts(prev => prev.filter(t => t.id !== id)); }, 3000);
  };

  const handleAddInstrument = async () => {
    if (!newInstrument) return;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/add_instrument', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: newInstrument.toUpperCase() }),
      });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); }
      else { addToast(result.message, 'success'); setNewInstrument(''); }
    } catch (error) { addToast('Error de red al añadir instrumento.', 'error'); }
  };

  const handleRemoveInstrument = async (instrumentToRemove: string) => {
    if (!window.confirm(`¿Seguro que quieres eliminar ${instrumentToRemove}?`)) return;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/remove_instrument', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: instrumentToRemove }),
      });
      const result = await response.json();
      if (!response.ok) { addToast(result.detail, 'error'); }
      else {
        addToast(result.message, 'success');
        if (activeTab === instrumentToRemove) {
          const remainingKeys = instrumentKeys.filter(k => k !== instrumentToRemove);
          setActiveTab(remainingKeys[0] || '');
        }
      }
    } catch (error) { addToast('Error de red al eliminar instrumento.', 'error'); }
  };

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/market_data');
    ws.onopen = () => setConnectionStatus('Conectado');
    ws.onerror = () => setConnectionStatus('Error de conexión');
    ws.onclose = () => setConnectionStatus('Desconectado');
    ws.onmessage = (event) => { const messageData: WsData = JSON.parse(event.data); setWsData(messageData); };
    return () => ws.close();
  }, []);

  const getProfitStyle = (profit: number) => { const color = profit >= 0 ? '#28a745' : '#dc3545'; return { color: color, fontWeight: 'bold' }; };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace', textAlign: 'center' }}>
      <h1>Trading Dashboard</h1>
      <p>Estado de Conexión: {connectionStatus}</p>
      <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1000 }}>
        {toasts.map(toast => ( <div key={toast.id} style={{ padding: '15px', marginBottom: '10px', borderRadius: '5px', color: 'white', backgroundColor: toast.type === 'success' ? 'rgba(40, 167, 69, 0.9)' : 'rgba(220, 53, 69, 0.9)', boxShadow: '0 2px 10px rgba(0,0,0,0.2)' }}>{toast.message}</div> ))}
      </div>
      {wsData?.account && ( <div style={{ border: '2px solid #333', backgroundColor: '#f0f0f0', padding: '10px', margin: '20px auto', maxWidth: '800px', borderRadius: '10px', display: 'flex', justifyContent: 'space-around' }}>
          <div><h4 style={{ margin: '0 0 5px 0' }}>BALANCE</h4><p style={{ margin: 0, fontSize: '18px' }}>{wsData.account.balance.toFixed(2)}</p></div>
          <div><h4 style={{ margin: '0 0 5px 0' }}>EQUITY</h4><p style={{ margin: 0, fontSize: '18px' }}>{wsData.account.equity.toFixed(2)}</p></div>
          <div><h4 style={{ margin: '0 0 5px 0' }}>PROFIT FLOTANTE</h4><p style={{ margin: 0, fontSize: '18px', ...getProfitStyle(wsData.account.profit) }}>{wsData.account.profit.toFixed(2)}</p></div>
        </div>
      )}
      <div style={{ border: '1px solid #ccc', borderRadius: '8px', margin: '30px auto', maxWidth: '900px' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #ccc', backgroundColor: '#f8f9fa', alignItems: 'center' }}>
          {instrumentKeys.map(instrumentName => (
            <div key={instrumentName} style={{ position: 'relative' }}>
              <button onClick={() => setActiveTab(instrumentName)} style={{
                padding: '10px 20px', paddingRight: '30px', border: 'none', background: activeTab === instrumentName ? 'white' : 'transparent',
                borderRight: '1px solid #ccc', cursor: 'pointer', fontWeight: activeTab === instrumentName ? 'bold' : 'normal'
              }}>
                {instrumentName}
              </button>
              <button onClick={() => handleRemoveInstrument(instrumentName)} style={{
                position: 'absolute', top: '50%', right: '5px', transform: 'translateY(-50%)',
                background: 'transparent', border: 'none', cursor: 'pointer', color: '#999',
                fontWeight: 'bold', fontSize: '16px'
              }}>
                &times;
              </button>
            </div>
          ))}
          <div style={{ padding: '5px', marginLeft: 'auto' }}>
            <input 
              type="text" 
              value={newInstrument}
              onChange={(e) => setNewInstrument(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAddInstrument(); }}
              placeholder="Añadir símbolo..."
              style={{ padding: '5px', border: '1px solid #ccc', borderRadius: '3px' }}
            />
            <button onClick={handleAddInstrument} style={{ marginLeft: '5px', padding: '5px 10px', cursor: 'pointer' }}>+</button>
          </div>
        </div>
        {wsData && activeTab && wsData[activeTab] && (
          <InstrumentPanel instrumentName={activeTab} instrumentData={wsData[activeTab] as InstrumentData} addToast={addToast} />
        )}
      </div>
    </div>
  );
}

export default App;