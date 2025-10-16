from app.extensions import db

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Setting {self.key}>'