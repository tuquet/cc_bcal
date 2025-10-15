import sys, os
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
	sys.path.insert(0, repo)
import app_core, sqlite3
print('project_root=', app_core.project_root)
app_core.ensure_db_columns()
dbpath=os.path.join(app_core.project_root,'database.db')
print('database=', dbpath)
conn=sqlite3.connect(dbpath)
cur=conn.cursor()
res=cur.execute("PRAGMA table_info('scripts')").fetchall()
print('columns:', [r[1] for r in res])
conn.close()
