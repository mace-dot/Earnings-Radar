"""Live isolation check using temporary accounts; no emails sent or secrets logged."""
import json,os,secrets,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from web.api._store import Store
s=Store();created=[];base=s.url
headers={'apikey':s.key,'Content-Type':'application/json'}
if not s.key.startswith('sb_secret_'):headers['Authorization']='Bearer '+s.key

def call(path,body=None,token=None,method=None):
 h=dict(headers)
 if token:h['Authorization']='Bearer '+token
 req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=h,method=method)
 with urlopen(req,timeout=20) as r:
  data=r.read();return json.loads(data) if data else None
try:
 sessions=[]
 for _ in range(2):
  email='radar-test-'+uuid.uuid4().hex+'@example.invalid';password=secrets.token_urlsafe(30)
  u=call('/auth/v1/admin/users',{'email':email,'password':password,'email_confirm':True});created.append(u['id'])
  session=call('/auth/v1/token?grant_type=password',{'email':email,'password':password});sessions.append(session['access_token'])
 call('/rest/v1/radar_watchlists',{'user_id':created[0],'symbol':'TSLA'},sessions[0])
 own=call('/rest/v1/radar_watchlists?select=symbol',token=sessions[0]);other=call('/rest/v1/radar_watchlists?select=symbol',token=sessions[1])
 assert any(r['symbol']=='TSLA' for r in own) and other==[]
 try:
  call('/rest/v1/radar_watchlists',{'user_id':created[0],'symbol':'MSFT'},sessions[1]);raise AssertionError('Cross-user write permitted')
 except HTTPError as e:assert e.code in (401,403)
 print('Live authentication and RLS verified: own watchlist visible; cross-user reads/writes blocked')
finally:
 for uid in created:call('/auth/v1/admin/users/'+uid,method='DELETE')
 print('Temporary test accounts and watchlists removed')
