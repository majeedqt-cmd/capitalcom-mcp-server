"""NOOR V2 alert-only worker. No order or account-change endpoints exist here.

Runs in a separate process alongside the existing MCP server. Uses a separate
in-memory Demo session; never reads/writes the SDK's shared session state.
"""
import asyncio
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import time
import urllib.request

BASE = 'https://demo-api-capital.backend-capital.com/api/v1'
WS = 'wss://api-streaming-capital.backend-capital.com/connect'
ROOT = pathlib.Path(__file__).resolve().parent
TF = {'HOUR': 3600, 'MINUTE_30': 1800, 'MINUTE_5': 300}


def log(event, **fields):
    print(json.dumps({'system': 'NOOR_LIVE_V2', 'time': time.time(),
                      'event': event, **fields}, ensure_ascii=False), flush=True)


def ema(values, period):
    if len(values) < period:
        raise ValueError('insufficient history')
    result = [None] * (period - 1) + [sum(values[:period]) / period]
    for value in values[period:]:
        result.append(result[-1] + 2 / (period + 1) * (value - result[-1]))
    return result


def wilder(values, period):
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = (value * (period - 1) + item) / period
    return value


def indicators(bars, cfg):
    closes = [b['c'] for b in bars]
    fast = ema(closes, cfg['ema_fast'])
    slow = ema(closes, cfg['ema_slow'])
    short = ema(closes, cfg['macd'][0])
    long = ema(closes, cfg['macd'][1])
    macd = [a-b for a, b in zip(short, long) if a is not None and b is not None]
    signal = ema(macd, cfg['macd'][2])[-1]
    changes = [b-a for a, b in zip(closes, closes[1:])]
    gain = wilder([max(0, v) for v in changes], cfg['rsi'])
    loss = wilder([max(0, -v) for v in changes], cfg['rsi'])
    rsi = 50 if gain == loss == 0 else 100 if loss == 0 else 100-100/(1+gain/loss)
    tr = [max(b['h']-b['l'], abs(b['h']-a['c']), abs(b['l']-a['c']))
          for a, b in zip(bars, bars[1:])]
    atr = wilder(tr, cfg['atr'])
    return {'ema20': fast[-1], 'ema50': slow[-1], 'slope': fast[-1]-fast[-4],
            'macd': macd[-1], 'macd_signal': signal, 'histogram': macd[-1]-signal,
            'rsi': rsi, 'atr': atr, 'close': closes[-1]}


def trend(ind, cfg):
    a = ind['atr']
    if a <= 0 or abs(ind['ema20']-ind['ema50']) < a*cfg['min_ema_separation_atr']:
        return 0
    direction = 1 if ind['ema20'] > ind['ema50'] else -1
    if direction*ind['slope'] < a*cfg['min_slope_atr']:
        return 0
    if direction*(ind['close']-ind['ema20']) <= 0:
        return 0
    # Indicators confirm, without requiring literal agreement from every one.
    score = int(direction*ind['macd'] > 0)
    score += int(direction*ind['histogram'] > 0)
    bounds=cfg['buy_rsi_range'] if direction==1 else cfg['sell_rsi_range']
    score += int(bounds[0] < ind['rsi'] < bounds[1])
    return direction if score >= cfg['min_indicator_confirmations'] else 0


def size_plan(entry, stop, target, spread, instrument, rules, cfg):
    if instrument.get('currency') != 'USD' or instrument.get('marginFactorUnit') != 'PERCENTAGE':
        return None
    if instrument.get('lotSize') != 1:
        return None  # fail closed for an unverified contract convention
    step = float(rules['minSizeIncrement']['value'])
    minimum = float(rules['minDealSize']['value'])
    factor = float(instrument['marginFactor'])/100
    distance = abs(entry-stop)
    reward = abs(target-entry)
    cost = spread + cfg['slippage_points']
    if min(step, factor, distance, reward-cost) <= 0:
        return None
    # Entry uses the executable side. Reserve additional spread + slippage as
    # a conservative cost allowance rather than claiming an exact fill price.
    risk_per_unit = distance + cost
    qty = min(cfg['margin_usd']/(entry*factor), cfg['max_risk_usd']/risk_per_unit)
    qty = math.floor((qty+1e-10)/step)*step
    qty = round(qty, 8)
    margin = qty*entry*factor
    risk, profit = qty*risk_per_unit, qty*(reward-cost)
    if qty < minimum or margin < cfg['margin_usd']*(1-cfg['margin_tolerance']):
        return None
    if risk > cfg['max_risk_usd'] or risk <= 0 or profit < cfg['min_reward_usd']:
        return None
    if profit/risk < cfg['min_net_rr']:
        return None
    for name, dist in [('minStopOrProfitDistance', min(distance, reward)),
                       ('maxStopOrProfitDistance', max(distance, reward))]:
        rule = rules[name]
        limit = float(rule['value'])*(entry/100 if rule['unit']=='PERCENTAGE' else 1)
        if name.startswith('min') and dist < limit or name.startswith('max') and dist > limit:
            return None
    return {'quantity': qty, 'margin_usd': margin, 'risk_usd': risk,
            'profit_usd': profit, 'net_rr': profit/risk, 'cost_allowance_usd': qty*cost}


def candidate(hist, quote, market, cfg, now):
    if quote['epic'] != 'GOLD' or not 0 <= now-quote['timestamp']/1000 <= cfg['stale_seconds']:
        return None
    if market['snapshot']['marketStatus'] != 'TRADEABLE':
        return None
    if market['snapshot'].get('scalingFactor',1)!=1:
        return None
    for key, seconds in TF.items():
        bars = hist[key]
        if len(bars) < 100 or not 0 <= now-(bars[-1]['t']+seconds) < seconds+10:
            return None
    inds = {key: indicators(hist[key], cfg) for key in TF}
    direction = trend(inds['HOUR'], cfg)
    if not direction or direction != trend(inds['MINUTE_30'], cfg):
        return None
    m5, ind = hist['MINUTE_5'], inds['MINUTE_5']
    bid, offer = float(quote['bid']), float(quote['ofr'])
    if bid <= 0 or offer < bid or offer-bid > ind['atr']*cfg['max_spread_atr']:
        return None
    last = m5[-1]
    if direction*(last['c']-last['o']) <= 0:
        return None
    pullback = any(b['l'] <= ind['ema20']+ind['atr']*cfg['pullback_atr'] and
                   b['h'] >= ind['ema20']-ind['atr']*cfg['pullback_atr'] for b in m5[-4:-1])
    if not pullback or direction*(last['c']-ind['ema20']) <= 0:
        return None
    # A fresh tick confirms resumption beyond the last closed M5 bar. Avoid
    # chasing a break that has already moved more than 0.2 ATR.
    trigger = last['h'] if direction == 1 else last['l']
    price = bid if direction == 1 else offer
    move = direction*(price-trigger)
    if not 0 <= move <= ind['atr']*cfg['max_chase_atr']:
        return None
    entry = offer if direction == 1 else bid
    setup=min(m5[-cfg['stop_lookback']:],key=lambda b:b['l']) if direction==1 else max(m5[-cfg['stop_lookback']:],key=lambda b:b['h'])
    stop = setup['l']-ind['atr']*cfg['stop_buffer_atr'] if direction==1 else setup['h']+ind['atr']*cfg['stop_buffer_atr']
    if direction*(entry-stop) <= 0:
        return None
    # Nearest confirmed swing level across M5/M30/H1 limits available reward.
    lows, highs = [], []
    for bars in hist.values():
        for i in range(max(2, len(bars)-70), len(bars)-2):
            if bars[i]['h'] >= max(b['h'] for b in bars[i-2:i+3]):
                highs.append(bars[i]['h'])
            if bars[i]['l'] <= min(b['l'] for b in bars[i-2:i+3]):
                lows.append(bars[i]['l'])
    resistance = min((h for h in highs if h > entry), default=None)
    support = max((l for l in lows if l < entry), default=None)
    level = resistance if direction == 1 else support
    if level is None:
        return None  # no invented distant target
    target = level-direction*ind['atr']*cfg['target_buffer_atr']
    plan = size_plan(entry, stop, target, offer-bid, market['instrument'], market['dealingRules'], cfg)
    if plan is None:
        return None
    return {'id': f"{cfg['version']}:GOLD:{direction}:{setup['t']}",
            'version': cfg['version'], 'direction': 'BUY' if direction == 1 else 'SELL',
            'created_at': now, 'source_at': quote['timestamp']/1000,
            'expires_at': min(now+cfg['expiry_seconds'], last['t']+600),
            'entry': entry, 'entry_zone': sorted([entry, entry+direction*ind['atr']*cfg['entry_zone_atr']]),
            'stop': stop, 'target': target, 'support': support, 'resistance': resistance,
            'indicators': inds, 'plan': plan, 'bid': bid, 'offer': offer,
            'reason': 'اتفاق اتجاه H1 وM30؛ تراجع M5 قرب EMA20 ثم شمعة استئناف وكسر مؤكد بالسعر المباشر.',
            'kind': 'signal', 'executed': False}


def message(s):
    p=s['plan']
    lines=[f"GOLD — {'شراء' if s['direction']=='BUY' else 'بيع'} | NOOR V2 Demo",
           f"السوق {s['bid']:.2f} / {s['offer']:.2f} | {dt.datetime.fromtimestamp(s['created_at'], dt.timezone(dt.timedelta(hours=4))).isoformat()}",
           f"الدخول {s['entry_zone'][0]:.2f}–{s['entry_zone'][1]:.2f} | الحجم {p['quantity']:.2f} | هامش ≈${p['margin_usd']:.2f}"]
    for tf, label in [('HOUR','H1'),('MINUTE_30','M30'),('MINUTE_5','M5')]:
        i=s['indicators'][tf]
        lines.append(f"{label}: EMA20/50 {i['ema20']:.2f}/{i['ema50']:.2f} | MACD {i['macd']:.2f}/{i['macd_signal']:.2f} | RSI {i['rsi']:.1f} | ATR {i['atr']:.2f}")
    lines += [f"اتجاه H1 وM30: {s['direction']}", f"الدعم {s['support']} | المقاومة {s['resistance']}",
              f"وقف {s['stop']:.2f} | هدف {s['target']:.2f}",
              f"خسارة مخططة ≈${p['risk_usd']:.2f} | ربح ≈${p['profit_usd']:.2f} | صافي R:R {p['net_rr']:.2f}",
              s['reason'], f"تنتهي {dt.datetime.fromtimestamp(s['expires_at'], dt.timezone(dt.timedelta(hours=4))).isoformat()}",
              'تُلغى بخروج السعر من منطقة الدخول أو تغير الاتجاه أو قدم البيانات. راجعها قبل التنفيذ اليدوي؛ ليست صفقة منفذة.',
              'التقديرات تشمل السبريد واحتياط انزلاق؛ الخسارة الفعلية قد تتجاوز الوقف.', f"ID: {s['id']}"]
    return '\n'.join(lines)


class DemoAPI:
    def __init__(self, cfg):
        self.cfg=cfg
        self.headers={'Content-Type':'application/json','X-CAP-API-KEY':os.environ['CAP_API_KEY']}

    def call(self, path, payload=None):
        # Hard allowlist: even a programming/configuration error cannot send a trade.
        allowed = path in ['/session', '/accounts', '/positions', '/markets/GOLD', '/ping'] or path.startswith('/prices/GOLD?')
        if not allowed or payload is not None and path != '/session':
            raise RuntimeError('READ_ONLY_POLICY')
        data=None if payload is None else json.dumps(payload).encode()
        request=urllib.request.Request(BASE+path, data=data, headers=self.headers,
                                       method='GET' if data is None else 'POST')
        with urllib.request.urlopen(request, timeout=12) as response:
            if path == '/session':
                self.headers['CST']=response.headers['CST']
                self.headers['X-SECURITY-TOKEN']=response.headers['X-SECURITY-TOKEN']
            result=json.load(response)
            if path=='/positions' and not isinstance(result.get('positions'),list):
                raise RuntimeError('POSITION_CACHE_INVALID')
            return result

    def login(self):
        if os.environ.get('CAP_ENV', '').lower() != 'demo':
            raise RuntimeError('DEMO_ENV_REQUIRED')
        s=self.call('/session', {'identifier':os.environ['CAP_IDENTIFIER'],
                                'password':os.environ['CAP_API_PASSWORD'], 'encryptedPassword':False})
        if str(s.get('currentAccountId')) != self.cfg['account_id']:
            raise RuntimeError('NOOR_ACCOUNT_MISMATCH_NO_SWITCH_ATTEMPTED')
        accounts=self.call('/accounts')['accounts']
        account=next(a for a in accounts if str(a['accountId'])==self.cfg['account_id'])
        if account['currency']!='USD' or account['accountName'].lower()!='noor live trading 1':
            raise RuntimeError('NOOR_ACCOUNT_IDENTITY_MISMATCH')

    def history(self):
        result={}
        now=time.time()
        for tf, seconds in TF.items():
            data=self.call(f"/prices/GOLD?resolution={tf}&max={self.cfg['history_bars']}")
            bars=[]
            for p in data['prices']:
                stamp=p.get('snapshotTimeUTC')
                if not stamp:
                    raise RuntimeError('UTC_CANDLE_TIMESTAMP_REQUIRED')
                t=dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).replace(tzinfo=dt.timezone.utc).timestamp()
                if t+seconds > now:
                    continue
                def mid(name):
                    pair=p[name]
                    return (float(pair['bid'])+float(pair['ask']))/2
                bars.append({'t':t,'o':mid('openPrice'),'h':mid('highPrice'),
                             'l':mid('lowPrice'),'c':mid('closePrice')})
            result[tf]=sorted(bars,key=lambda b:b['t'])
        return result


async def relay(payload):
    url=os.environ['NOOR_V2_RELAY_URL']
    def send():
        req=urllib.request.Request(url, data=json.dumps(payload).encode(),
             headers={'Content-Type':'application/json',
                      'X-Noor-Token':os.environ['NOOR_V2_RELAY_TOKEN']}, method='POST')
        with urllib.request.urlopen(req,timeout=10) as response:
            return json.load(response)
    return await asyncio.to_thread(send)


async def connected(cfg, startup_test=False):
    import websockets
    api=DemoAPI(cfg)
    await asyncio.to_thread(api.login)
    market=await asyncio.to_thread(api.call,'/markets/GOLD')
    if not market['instrument'].get('streamingPricesAvailable'):
        raise RuntimeError('STREAM_NOT_AVAILABLE')
    hist=await asyncio.to_thread(api.history)
    positions=await asyncio.to_thread(api.call,'/positions')
    log('history_ready',bars={k:len(v) for k,v in hist.items()},account=cfg['account_id'])
    last_refresh=time.time(); last_ping=time.time(); last_health=0
    last_bucket=int(time.time()/300)
    pending=None; seen=set(); tick_count=0
    async with websockets.connect(WS, open_timeout=12, ping_interval=20, ping_timeout=10) as ws:
        auth={'cst':api.headers['CST'],'securityToken':api.headers['X-SECURITY-TOKEN']}
        await ws.send(json.dumps({'destination':'marketData.subscribe','correlationId':'NOOR-V2',
                                  **auth,'payload':{'epics':['GOLD']}}))
        async for raw in with_timeout(ws, cfg['reconnect_seconds']):
            received=time.time()
            data=json.loads(raw)
            if data.get('status') not in [None,'OK']:
                raise RuntimeError('WS_SERVER_ERROR')
            if data.get('destination')!='quote':
                continue
            q=data['payload']
            if q.get('epic')!='GOLD':
                continue
            if not 0 <= received-float(q['timestamp'])/1000 <= cfg['stale_seconds']:
                log('stale_quote_suppressed'); continue
            tick_count+=1
            if startup_test:
                payload={'id':'V2-e2e-'+os.environ['NOOR_V2_DEPLOY_ID'], 'kind':'test',
                         'created_at':received, 'expires_at':received+60,
                         'source_at':q['timestamp']/1000, 'executed':False,
                         'message':f"NOOR V2 — اختبار شامل من بث GOLD المباشر إلى Slack.\nالسعر {q['bid']} / {q['ofr']}\nوقت المصدر UTC: {dt.datetime.fromtimestamp(q['timestamp']/1000,dt.timezone.utc).isoformat()}\nاختبار تقني فقط، ليس إشارة أو صفقة. الرمز: {os.environ['NOOR_V2_DEPLOY_ID']}"}
                result=await relay(payload)
                if not result.get('ok'):
                    raise RuntimeError('RELAY_E2E_NOT_ACKNOWLEDGED')
                log('e2e_ack',source_to_ack_ms=round((time.time()-q['timestamp']/1000)*1000),
                    source_to_slack_ms=result.get('source_to_slack_ms'),slack_ts=result.get('slack_ts'))
                startup_test=False
            if received-last_ping > 240:
                await ws.send(json.dumps({'destination':'ping','correlationId':'keepalive',**auth}))
                await asyncio.to_thread(api.call,'/ping'); last_ping=received
            # Read-only account occupancy and market availability refresh. A stale
            # occupancy cache blocks alerts rather than assuming an empty account.
            if received-last_refresh > 15:
                positions=await asyncio.to_thread(api.call,'/positions')
                market=await asyncio.to_thread(api.call,'/markets/GOLD')
                last_refresh=time.time()
            bucket=int(received/300)
            if bucket != last_bucket:
                hist=await asyncio.to_thread(api.history)
                last_bucket=bucket
                pending=None
                log('closed_candles_refreshed',bars={k:v[-1]['t'] for k,v in hist.items()})
            # A quote may age while REST calls are running. candidate checks it again.
            now=time.time()
            if now-last_refresh > 20 or len(positions.get('positions',[])) >= cfg['max_simultaneous_positions']:
                pending=None; continue
            if pending and now < pending['expires_at']:
                continue  # one active proposed opportunity at a time
            s=candidate(hist,q,market,cfg,now)
            if s and s['id'] not in seen:
                s['message']=message(s)
                result=await relay(s)
                if not result.get('ok'):
                    raise RuntimeError('RELAY_NOT_ACKNOWLEDGED')
                seen.add(s['id']); pending=s
                log('signal_sent',signal=s,source_to_ack_ms=round((time.time()-s['source_at'])*1000),
                    slack_ts=result.get('slack_ts'))
            if now-last_health >= 60:
                log('stream_healthy',ticks=tick_count,source_age_ms=round((now-q['timestamp']/1000)*1000),
                    open_positions=len(positions.get('positions',[])),version=cfg['version'])
                last_health=now


async def with_timeout(ws, seconds):
    while True:
        yield await asyncio.wait_for(ws.recv(),seconds)


async def worker():
    baseline=json.loads((ROOT/'noor_v2_config.json').read_text())
    # Whole approved configurations only; no automatic edits or adaptation.
    cfg=json.loads(os.environ.get('NOOR_V2_CONFIG', json.dumps(baseline)))
    cfg['account_id']=os.environ['NOOR_V2_ACCOUNT_ID']
    if cfg['epic']!='GOLD' or cfg['max_risk_usd']>10 or cfg['min_net_rr']<1.5 or cfg['max_simultaneous_positions']!=1:
        raise RuntimeError('APPROVED_LIMITS_VIOLATION')
    log('worker_start',version=cfg['version'],config_sha256=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest())
    delay=1
    while cfg['enabled']:
        started=time.time()
        try:
            await connected(cfg,startup_test=True)
        except Exception as exc:
            # Do not log exception text, headers, URLs or API response bodies.
            log('connection_lost_signals_paused',error_type=type(exc).__name__)
        if time.time()-started>60: delay=1
        await asyncio.sleep(delay+random.random())
        delay=min(60,delay*2)


def supervise():
    # Preserve the existing MCP invocation. The worker has no access to its
    # in-process context or on-disk token cache. Restart worker independently.
    mcp=subprocess.Popen([sys.executable,'-m','capital_mcp','run','--transport','http',
                           '--host','0.0.0.0','--port',os.environ.get('PORT','8000')])
    monitor=None
    try:
        while mcp.poll() is None:
            if monitor is None or monitor.poll() is not None:
                monitor=subprocess.Popen([sys.executable,__file__,'worker'])
            time.sleep(2)
    finally:
        if monitor: monitor.terminate()
        mcp.terminate()
    sys.exit(mcp.returncode or 0)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='supervise': supervise()
    else: asyncio.run(worker())
