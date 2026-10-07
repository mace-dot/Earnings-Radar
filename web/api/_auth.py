"""Supabase session validation with HttpOnly cookies; no client-supplied user IDs."""
import json
import os
import uuid
from http.cookies import SimpleCookie
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

class AuthError(RuntimeError):pass

def auth_request(store,path,payload=None,token=None):
    key=os.getenv('SUPABASE_ANON_KEY') or store.key
    headers={'apikey':key,'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    try:
        with urlopen(Request(store.url+'/auth/v1/'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers),timeout=15) as r:
            return json.load(r)
    except HTTPError:raise AuthError('Authentication failed. Check your credentials and email confirmation.') from None
    except URLError:raise AuthError('Authentication service unavailable') from None

def current_user(store,cookie):
    c=SimpleCookie();c.load(cookie or '');value=c.get('radar_session')
    if not value:raise AuthError('Sign in to save your watchlist')
    user=auth_request(store,'user',token=value.value)
    try:user['id']=str(uuid.UUID(user['id']))
    except (ValueError,KeyError):raise AuthError('Invalid session') from None
    return user

def cookie(name,value,max_age):
    c=SimpleCookie();c[name]=value;c[name]['path']='/';c[name]['httponly']=True;c[name]['secure']=True;c[name]['samesite']='Lax';c[name]['max-age']=max_age
    return c[name].OutputString()
