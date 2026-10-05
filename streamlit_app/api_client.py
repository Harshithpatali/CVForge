import os
import requests

API_URL = os.getenv('CVFORGE_API_URL', 'http://localhost:8000').rstrip('/')

class APIError(Exception):
    pass

def request(method, path, token=None, **kwargs):
    headers=kwargs.pop('headers', {})
    if token: headers['Authorization']=f'Bearer {token}'
    try:
        r=requests.request(method, f'{API_URL}{path}', headers=headers, timeout=180, **kwargs)
    except requests.RequestException as exc:
        raise APIError(f'Cannot reach CVForge API: {exc}') from exc
    if not r.ok:
        try: detail=r.json().get('detail', r.text)
        except Exception: detail=r.text
        raise APIError(f'{r.status_code}: {detail}')
    return r

def auth(path,payload): return request('POST',path,json=payload).json()
def get(path,token): return request('GET',path,token=token).json()
def post(path,token,**kwargs): return request('POST',path,token=token,**kwargs).json()
def put(path,token,**kwargs): return request('PUT',path,token=token,**kwargs).json()
