from CTFd.models import db

# General database tables go in this file
class challengeVM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    template = db.Column(db.String(80))
    description = db.Column(db.Text)
    dns_id = db.Column(db.Integer, db.ForeignKey('challengeDNS.id'))

    def __init__(self, name, template, description, dns_id):
        self.name = name
        self.template = template
        self.description = description
        self.dns_id = dns_id

class challengeDNS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone = db.Column(db.String(253))
    label = db.Column(db.String(63))

    def __init__(self, zone, label):
        self.zone = zone
        self.label = label
