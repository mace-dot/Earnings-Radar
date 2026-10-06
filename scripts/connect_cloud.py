"""Connect existing authorized Supabase/Vercel projects. Never prints credentials."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

REF = 'fepyjsmmgortycprrxjr'
ALIAS = 'earnings-radar-two.vercel.app'
ROOT = Path(__file__).resolve().parents[1]


def request(host, path, token, payload=None, method=None):
    req = Request('https://'+host+path, headers={'Authorization': 'Bearer '+token, 'Content-Type':'application/json'},
                  data=json.dumps(payload).encode() if payload is not None else None, method=method)
    try:
        with urlopen(req, timeout=45) as r: return json.loads(r.read())
    except HTTPError as exc:
        raise RuntimeError(f'{host}: HTTP {exc.code}; check account access') from None
    except URLError:
        raise RuntimeError(f'{host}: connection unavailable') from None


def main():
    st = os.getenv('SUPABASE_ACCESS_TOKEN'); vt = os.getenv('VERCEL_TOKEN')
    if not st or not vt:
        raise RuntimeError('Set SUPABASE_ACCESS_TOKEN and VERCEL_TOKEN securely in environment settings')
    # Read both project identities before applying any changes.
    project = request('api.supabase.com', '/v1/projects/'+REF, st)
    if project.get('id') != REF: raise RuntimeError('Unexpected Supabase project identity')
    alias = request('api.vercel.com', '/v4/aliases/'+ALIAS, vt)
    pid = alias.get('projectId') or alias.get('project',{}).get('id')
    if not pid: raise RuntimeError('Vercel alias did not resolve to a project')
    vp = request('api.vercel.com', '/v9/projects/'+pid, vt)
    link = vp.get('link',{})
    if link.get('type') != 'github' or link.get('repo') != 'Earnings-Radar' or link.get('org') != 'mace-dot':
        raise RuntimeError('Vercel project is not linked to the expected GitHub repository')
    if vp.get('rootDirectory') != 'web':
        raise RuntimeError('Set the Vercel project Root Directory to web before connecting')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not key:
        keys = request('api.supabase.com', '/v1/projects/'+REF+'/api-keys', st)
        key = next((k['api_key'] for k in keys if k.get('name')=='service_role'), None)
    if not key: raise RuntimeError('Server key unavailable; enter SUPABASE_SERVICE_ROLE_KEY securely')
    sql = (ROOT/'supabase/migrations/202610060001_radar.sql').read_text()
    request('api.supabase.com', '/v1/projects/'+REF+'/database/query', st, {'query':sql})
    request('api.vercel.com', '/v10/projects/'+pid+'/env?upsert=true', vt,
            [{'key':name,'value':value,'type':'encrypted','target':['production','preview']}
             for name,value in [('SUPABASE_URL','https://'+REF+'.supabase.co'),('SUPABASE_SERVICE_ROLE_KEY',key)]])
    os.environ['SUPABASE_URL'] = 'https://'+REF+'.supabase.co'
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = key
    from earnings_radar.worker import Worker
    from earnings_radar.cloud_sync import publish
    from tempfile import TemporaryDirectory
    os.environ.setdefault('SEC_USER_AGENT','EarningsRadar mace@udel.edu')
    with TemporaryDirectory(prefix='radar-connect-') as tmp:
        path = Path(tmp)/'research.db'; Worker(path).run(once=True)
        count = publish(path)
    if count == 0: raise RuntimeError('Database connected but no source evidence collected; inspect source access')
    deployment = request('api.vercel.com', '/v13/deployments', vt,
                         {'name':vp['name'],'project':pid,'target':'production',
                          'gitSource':{'type':'github','repoId':link['repoId'],'ref':'main'}})
    print(f'Database initialized; {count} validated records published; production deployment requested.')
    print('Check https://'+ALIAS+'/api/dashboard after Vercel finishes building.')
    print('Hourly collection still requires GitHub Actions secrets and RADAR_CLOUD_ENABLED=true.')

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    try: main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(1)
