#!/usr/bin/env python3
"""Fetch public Google News RSS summaries; export a dated feed, no API key."""
import json, re, pathlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'news.json'
NOW=datetime.now(timezone.utc)
FEEDS=[
 ('kr','코스피 OR 코스닥 OR 삼성전자 OR SK하이닉스 when:2d','ko','KR','KR:ko'),
 ('kr','한국 증시 반도체 금융 금리 환율 when:2d','ko','KR','KR:ko'),
 ('us','stock market OR Nasdaq OR S&P 500 when:2d','en-US','US','US:en'),
 ('us','Nvidia OR Tesla OR Fed OR earnings when:2d','en-US','US','US:en'),
]
TICKERS={'삼성전자':'005930','SK하이닉스':'000660','현대차':'005380','기아':'000270','네이버':'035420','NAVER':'035420','카카오':'035720','LG에너지솔루션':'373220','엔비디아':'NVDA','Nvidia':'NVDA','NVDA':'NVDA','테슬라':'TSLA','Tesla':'TSLA','애플':'AAPL','Apple':'AAPL','마이크로소프트':'MSFT','Microsoft':'MSFT','아마존':'AMZN','Amazon':'AMZN','구글':'GOOGL','Alphabet':'GOOGL','메타':'META','Meta':'META','AMD':'AMD','TSMC':'TSM'}
POS=('상승','급등','호실적','최대 실적','수주','성장','반등','돌파','surge','rally','beat estimates','gain','record high','jump')
NEG=('하락','급락','적자','부진','악화','감소','경고','소송','폭락','plunge','slump','miss estimates','fall','decline','drop')
def clean(s): return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()
def fetch(category,query,hl,gl,ceid):
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':hl,'gl':gl,'ceid':ceid})
    req=urllib.request.Request(url,headers={'User-Agent':'PULSE-NewsDigest/1.0 (+public RSS reader)','Accept':'application/rss+xml,application/xml,text/xml'})
    with urllib.request.urlopen(req,timeout=22) as r: body=r.read(2_500_000)
    xml=ET.fromstring(body)
    result=[]
    for item in xml.findall('.//channel/item')[:70]:
        title=clean(item.findtext('title')); url=(item.findtext('link') or '').strip()
        if not title or not url.startswith('https://'): continue
        try: d=parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
        except (ValueError,TypeError,AttributeError): continue
        if d < NOW-timedelta(hours=72) or d>NOW+timedelta(hours=1): continue
        source=clean(item.findtext('source')) or 'Google 뉴스'
        stocks=[]
        for name,ticker in TICKERS.items():
            if (re.search(r'(?<![a-zA-Z])'+re.escape(name)+r'(?![a-zA-Z])',title,re.I) if name.isascii() else name in title) and ticker not in [x['ticker'] for x in stocks]:
                stocks.append({'name':name,'ticker':ticker})
        t=title.lower();pos=sum(w.lower() in t for w in POS);neg=sum(w.lower() in t for w in NEG)
        sentiment='긍정 표현' if pos>neg else '부정 표현' if neg>pos else '중립/불명'
        result.append({'type':category,'title':title[:220],'url':url,'source':source[:90],'published':d.isoformat(),'stocks':stocks[:5],'sentiment':sentiment})
    return result

def main():
    items=[]; errors=[]; ok=0
    for f in FEEDS:
        try:
            got=fetch(*f); items+=got; ok+=1; print(f[0],len(got))
        except Exception as e: errors.append(str(e)); print('feed error:',str(e))
    unique={}
    for item in items:
        # Google News variants dedup based on normalized title
        key=re.sub(r'[^\w\uac00-\ud7a3]','',re.sub(r'\s+[-–|]\s+[^-–|]{2,65}$','',item['title']).lower())[:130]
        if key and key not in unique: unique[key]=item
    final=sorted(unique.values(),key=lambda x:x['published'],reverse=True)[:100]
    # Avoid replacing existing content with an empty result due to temporary RSS failures.
    if not final:
        print('No recent items. Keep previous news.json unchanged.');return 0 if OUT.exists() else 1
    counts={}
    for a in final:
        for st in a['stocks']:counts[st['ticker']]=(st['name'],counts.get(st['ticker'],('',0))[1]+1)
    ranks=[{'name':v[0],'ticker':k,'mentions':v[1]} for k,v in sorted(counts.items(),key=lambda kv:-kv[1][1])[:10]]
    payload={'updated_at':NOW.isoformat(),'source_note':'Google 뉴스 공개 RSS 검색 결과. 조회수 기반 인기 순위나 실시간 시세가 아닙니다.','feed_count':ok,'articles':final,'top_stocks':ranks}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('saved',len(final),'articles', 'errors',len(errors));return 0
if __name__=='__main__': raise SystemExit(main())
