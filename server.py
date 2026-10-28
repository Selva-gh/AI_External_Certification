#!/usr/bin/env python3
# AI External Certification Tracker - local SQLite DB API server (stdlib only).
import json, os, re, sqlite3, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'certifications.db')
SEED_PATH = os.path.join(HERE, 'seed_data.json')
PORT = 8000
FIELDS = ['emp','name','jl','team','mgr','cert','status','planned','completion','area','remarks']
_lock = threading.Lock()

def get_conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; return c

CREATE_SQL = ('CREATE TABLE IF NOT EXISTS certifications ('
    'id INTEGER PRIMARY KEY AUTOINCREMENT, emp TEXT, name TEXT, jl TEXT, team TEXT,'
    'mgr TEXT, cert TEXT, status TEXT, planned TEXT, completion TEXT, area TEXT,'
    "remarks TEXT, created TEXT DEFAULT (datetime('now')),"
    "modified TEXT DEFAULT (datetime('now')))")

def init_db():
    with get_conn() as conn:
        conn.execute(CREATE_SQL); conn.commit()
        n = conn.execute('SELECT COUNT(*) c FROM certifications').fetchone()['c']
        if n == 0 and os.path.exists(SEED_PATH):
            with open(SEED_PATH, encoding='utf-8') as f: seed = json.load(f)
            rows = [tuple(r.get(k, '') for k in FIELDS) for r in seed]
            ph = ','.join(['?']*len(FIELDS))
            conn.executemany('INSERT INTO certifications (' + ','.join(FIELDS) + ') VALUES (' + ph + ')', rows)
            conn.commit(); print('[seed] inserted %d record(s)' % len(rows))
        else:
            print('[db] existing database with %d record(s)' % n)

def row_to_record(r):
    rec = {'id': 'db' + str(r['id']), 'dbId': r['id']}
    for k in FIELDS: rec[k] = r[k] if r[k] is not None else ''
    return rec

def dump_seed(conn):
    # Mirror the full DB into seed_data.json so the JSON always matches the DB.
    rows = conn.execute('SELECT * FROM certifications ORDER BY id').fetchall()
    data = [{k: (r[k] if r[k] is not None else '') for k in FIELDS} for r in rows]
    tmp = SEED_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SEED_PATH)
    return len(data)

class H(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers(); self.wfile.write(body)
    def _body(self):
        n = int(self.headers.get('Content-Length', 0))
        if not n: return {}
        try: return json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception: return {}
    def _id(self):
        m = re.match(r'^/api/records/(\d+)$', self.path); return int(m.group(1)) if m else None
    def log_message(self, *a): pass
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()
    def do_GET(self):
        if self.path == '/api/health':
            with _lock, get_conn() as conn:
                c = conn.execute('SELECT COUNT(*) c FROM certifications').fetchone()['c']
            return self._json({'ok': True, 'count': c})
        if self.path == '/api/records':
            with _lock, get_conn() as conn:
                rows = conn.execute('SELECT * FROM certifications ORDER BY id').fetchall()
            return self._json([row_to_record(r) for r in rows])
        rid = self._id()
        if rid is not None:
            with _lock, get_conn() as conn:
                r = conn.execute('SELECT * FROM certifications WHERE id=?', (rid,)).fetchone()
            return self._json(row_to_record(r)) if r else self._json({'error':'not found'}, 404)
        return self._static()
    def _static(self):
        path = self.path.split('?',1)[0].lstrip('/') or 'certification-tracker.html'
        safe = os.path.normpath(os.path.join(HERE, path))
        if not safe.startswith(HERE) or not os.path.isfile(safe):
            return self._json({'error':'not found'}, 404)
        ct = 'application/octet-stream'
        if safe.endswith('.html'): ct='text/html'
        elif safe.endswith('.json'): ct='application/json'
        elif safe.endswith('.js'): ct='application/javascript'
        elif safe.endswith('.css'): ct='text/css'
        with open(safe,'rb') as f: data=f.read()
        self.send_response(200)
        self.send_header('Content-Type', ct + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if self.path == '/api/sync':
            return self._sync()
        if self.path != '/api/records': return self._json({'error':'unknown'}, 404)
        d = self._body(); vals = [str(d.get(k,'') or '') for k in FIELDS]
        ph = ','.join(['?']*len(FIELDS))
        with _lock, get_conn() as conn:
            cur = conn.execute('INSERT INTO certifications (' + ','.join(FIELDS) + ') VALUES (' + ph + ')', vals)
            conn.commit(); nid = cur.lastrowid
            r = conn.execute('SELECT * FROM certifications WHERE id=?', (nid,)).fetchone()
            dump_seed(conn)
        return self._json(row_to_record(r), 201)
    def _sync(self):
        # Accept a batch of offline-queued operations and apply them.
        ops = self._body()
        if not isinstance(ops, list):
            return self._json({'error': 'expected a list of ops'}, 400)
        applied = {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0}
        ph = ','.join(['?']*len(FIELDS))
        setclause = ','.join(k + '=?' for k in FIELDS)
        with _lock, get_conn() as conn:
            for op in ops:
                try:
                    kind = op.get('op')
                    rec = op.get('record', {})
                    if kind == 'create':
                        vals = [str(rec.get(k,'') or '') for k in FIELDS]
                        conn.execute('INSERT INTO certifications (' + ','.join(FIELDS) + ') VALUES (' + ph + ')', vals)
                        applied['created'] += 1
                    elif kind == 'update' and rec.get('dbId'):
                        vals = [str(rec.get(k,'') or '') for k in FIELDS]
                        conn.execute("UPDATE certifications SET " + setclause + ", modified=datetime('now') WHERE id=?", vals + [int(rec['dbId'])])
                        applied['updated'] += 1
                    elif kind == 'delete' and rec.get('dbId'):
                        conn.execute('DELETE FROM certifications WHERE id=?', (int(rec['dbId']),))
                        applied['deleted'] += 1
                    else:
                        applied['errors'] += 1
                except Exception:
                    applied['errors'] += 1
            conn.commit()
            dump_seed(conn)
            rows = conn.execute('SELECT * FROM certifications ORDER BY id').fetchall()
        return self._json({'ok': True, 'applied': applied, 'records': [row_to_record(r) for r in rows]})

    def do_PUT(self):
        rid = self._id()
        if rid is None: return self._json({'error':'unknown'}, 404)
        d = self._body(); vals = [str(d.get(k,'') or '') for k in FIELDS]
        setclause = ','.join(k + '=?' for k in FIELDS)
        with _lock, get_conn() as conn:
            if not conn.execute('SELECT 1 FROM certifications WHERE id=?', (rid,)).fetchone():
                return self._json({'error':'not found'}, 404)
            conn.execute("UPDATE certifications SET " + setclause + ", modified=datetime('now') WHERE id=?", vals + [rid])
            conn.commit()
            r = conn.execute('SELECT * FROM certifications WHERE id=?', (rid,)).fetchone()
            dump_seed(conn)
        return self._json(row_to_record(r))
    def do_DELETE(self):
        rid = self._id()
        if rid is None: return self._json({'error':'unknown'}, 404)
        with _lock, get_conn() as conn:
            conn.execute('DELETE FROM certifications WHERE id=?', (rid,)); conn.commit()
            dump_seed(conn)
        return self._json({'ok': True, 'deleted': rid})

def main():
    init_db()
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print('')
    print('DB API running at http://localhost:%d' % PORT)
    print('Open the app:  http://localhost:%d/certification-tracker.html' % PORT)
    print('Database file: %s' % DB_PATH)
    print('Press Ctrl+C to stop.')
    try: srv.serve_forever()
    except KeyboardInterrupt: srv.shutdown()

if __name__ == '__main__':
    main()
