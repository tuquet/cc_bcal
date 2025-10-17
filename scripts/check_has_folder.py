from app import create_app
from app.extensions import db
from app.models.script import Script

app = create_app('default')
with app.app_context():
    s = db.session.execute(db.select(Script).limit(1)).scalars().all()
    print('queried', len(s), 'scripts')
    print('columns:', [c.name for c in Script.__table__.columns])
