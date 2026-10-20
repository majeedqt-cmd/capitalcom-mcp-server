import asyncio
import copy
import json
import pathlib
import unittest
from unittest.mock import patch
import noor_v2 as n

C=json.loads((pathlib.Path(__file__).parent/'noor_v2_config.json').read_text())
INSTRUMENT={'currency':'USD','marginFactorUnit':'PERCENTAGE','marginFactor':5,'lotSize':1}
RULES={'minSizeIncrement':{'value':0.01},'minDealSize':{'value':0.01},
       'minStopOrProfitDistance':{'unit':'PERCENTAGE','value':0.001},
       'maxStopOrProfitDistance':{'unit':'PERCENTAGE','value':100}}


class V2Safety(unittest.TestCase):
    def test_indicators_flat_and_monotonic(self):
        flat=[{'o':100,'h':101,'l':99,'c':100} for _ in range(220)]
        i=n.indicators(flat,C)
        self.assertEqual((i['rsi'],i['macd'],i['histogram'],i['atr']),(50,0,0,2))
        up=[{'o':x,'h':x+1,'l':x-1,'c':x} for x in range(1,221)]
        i=n.indicators(up,C)
        self.assertAlmostEqual(i['ema20'],210.5)
        self.assertAlmostEqual(i['ema50'],195.5)
        self.assertAlmostEqual(i['macd'],7)
        self.assertEqual(i['rsi'],100)

    def test_risk_margin_and_net_costs(self):
        p=n.size_plan(1000,990,1040,0.5,INSTRUMENT,RULES,C)
        self.assertIsNotNone(p)
        self.assertEqual(p['quantity'],0.4)
        self.assertEqual(p['margin_usd'],20)
        self.assertAlmostEqual(p['risk_usd'],4.4)
        self.assertAlmostEqual(p['profit_usd'],15.6)
        self.assertGreaterEqual(p['net_rr'],1.5)

    def test_reject_impossible_minimum_contract(self):
        r=copy.deepcopy(RULES);r['minDealSize']['value']=1
        self.assertIsNone(n.size_plan(4132,4122,4212,0.5,INSTRUMENT,r,C))

    def test_reject_excess_risk_or_low_reward(self):
        self.assertIsNone(n.size_plan(1000,900,1200,0.5,INSTRUMENT,RULES,C))
        self.assertIsNone(n.size_plan(1000,990,1010,0.5,INSTRUMENT,RULES,C))
        self.assertIsNone(n.size_plan(1000,990,1020,5,INSTRUMENT,RULES,C))

    def fixture(self,direction=1):
        now=1800000100
        h={}
        for tf,seconds in n.TF.items():
            end=(int(now)//seconds)*seconds-seconds
            bars=[{'t':end-(119-j)*seconds,'o':990,'h':999,'l':988,'c':995} for j in range(120)]
            bars[60]['h']=1040
            bars[65]['l']=950
            bars[-1].update(o=997,h=1000,l=995,c=999)
            h[tf]=bars
        ind={'ema20':993,'ema50':980,'slope':2,'macd':2,'macd_signal':1,'histogram':1,'rsi':60,'atr':10,'close':999}
        quote={'epic':'GOLD','bid':1000,'ofr':1000.5,'timestamp':now*1000}
        market={'instrument':INSTRUMENT,'dealingRules':RULES,'snapshot':{'marketStatus':'TRADEABLE'}}
        return now,h,ind,quote,market

    def test_valid_synthetic_opportunity_is_not_a_fill(self):
        now,h,i,q,m=self.fixture()
        with patch.object(n,'indicators',return_value=i):
            s=n.candidate(h,q,m,C,now)
        self.assertIsNotNone(s)
        self.assertFalse(s['executed'])
        self.assertEqual(s['direction'],'BUY')
        self.assertGreater(s['expires_at'],now)
        self.assertIn('ليست صفقة منفذة',n.message(s))

    def test_stale_future_and_missing_candles_block(self):
        now,h,i,q,m=self.fixture()
        with patch.object(n,'indicators',return_value=i):
            self.assertIsNone(n.candidate(h,q,m,C,now+6))
            q['timestamp']=(now+30)*1000
            self.assertIsNone(n.candidate(h,q,m,C,now))
            q['timestamp']=now*1000;h['HOUR'][-1]['t']+=3600
            self.assertIsNone(n.candidate(h,q,m,C,now))

    def test_choppy_or_conflicting_trends_block(self):
        now,h,i,q,m=self.fixture()
        sideways={**i,'ema50':i['ema20']}
        with patch.object(n,'indicators',return_value=sideways):
            self.assertIsNone(n.candidate(h,q,m,C,now))
        down={**i,'ema20':980,'ema50':993,'close':970,'slope':-2,'macd':-2}
        with patch.object(n,'indicators',side_effect=[i,down,i]):
            self.assertIsNone(n.candidate(h,q,m,C,now))

    def test_trade_and_account_mutations_are_impossible(self):
        with patch.dict(n.os.environ,{'CAP_API_KEY':'test'}):
            api=n.DemoAPI(C)
        for path in ['/positions','/workingorders','/session/switch','/accounts/preferences']:
            with self.assertRaisesRegex(RuntimeError,'READ_ONLY_POLICY'):
                api.call(path,{'direction':'BUY'})

    def test_disconnect_timeout_stops_stream(self):
        class DeadStream:
            async def recv(self):
                await asyncio.sleep(1)
        async def check():
            with self.assertRaises(asyncio.TimeoutError):
                await anext(n.with_timeout(DeadStream(),0.01))
        asyncio.run(check())


if __name__=='__main__': unittest.main()
