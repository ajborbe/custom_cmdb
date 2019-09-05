from flask import Flask, request, jsonify, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
db = SQLAlchemy(app)


DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    sched = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="Not Scanned")
    last_scan = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<Asset %r>' % self.url

@app.route('/rest/assets/', methods=['GET', 'POST'])
def assets():
    if request.method == 'POST':
        try:
            request_json = request.json or request.form.to_dict()
            print(request_json['sched'])
            # convert sched to python datetime object
            request_json['sched'] = datetime.strptime(request_json['sched'] + ':00', DATE_FORMAT)
            asset_record = Asset(**request_json)
            db.session.add(asset_record)
            db.session.commit()
            if request.json:
                return serializer(asset_record)
            elif request.form:
                return redirect(url_for('index'))
        except Exception as e:
            print(e)
            return jsonify({"status": "error malformed json request", "message": 'sample request: {"password": "password", "sched": "2019-09-02 16:32:55", "status": "Passed", "url": "https://news.ycombinator.com", "username": "username" }'})
    
    else:
        return jsonify([serializer(asset) for asset in Asset.query.all()])

@app.route('/rest/assets/<int:asset_id>/', methods=['GET'])
def asset(asset_id):
    return serializer(Asset.query.filter_by(id=asset_id).first())

@app.route('/rest/scan/', methods=['POST'])
def scan():
    if request.method == 'POST':
        try:
            if request.json:
                data = service_now(request.json['ids'])
                service_request(data)
                return jsonify(data)
            elif request.form:
                data = service_now(list(request.form.to_dict().values()))
                service_request(data)
                return redirect(url_for('index'))
        except Exception as e:
            print(e)
            return jsonify({"status": "error malformed json request", "message": 'sample request: {"ids": [1,2,3]}'})
    else:
        return jsonify([serializer(asset) for asset in Asset.query.all()])
        
@app.route('/', methods=['GET'])
def index():
    url = 'http://' + request.host + url_for('assets')
    data = requests.get(url)
    return render_template('table.html', data=data.json())

def service_now(record):
    data = Asset.query.filter(Asset.id.in_(record)).all()
    scans = {'auth':[], 'non-auth': []}
    for datum in data:
        if len(datum.username) == 0 and len(datum.password) == 0:
            sched = datum.sched.strftime(DATE_FORMAT)
            scans['non-auth'].append({
                'id': datum.id,
                'url': datum.url,
                'sched': sched
                })
        else:
            sched = datum.sched.strftime(DATE_FORMAT)
            scans['auth'].append({
                'id': datum.id,
                'url': datum.url,
                'username': datum.username,
                'password': datum.password,
                'sched': sched
                })
    return scans

def service_request(record):
    FILTER = "SCAN REQUEST"
    URL = 'https://dev68191.service-now.com/api/now/table/sc_request'
    USER = 'admin'
    PWD = 'Newhire123!@#'
    headers = {"Content-Type":"application/xml","Accept":"application/json"}
    data ="""
    <request>
            <entry>
                    <description> {0} </description>
                    <short_description> {1} </short_description>
                    <stage>requested</stage>
                    <approval>requested</approval>
                    <made_sla>true</made_sla>
            </entry>
    </request>""".format(record, FILTER)
    response = requests.post(URL, auth=(USER, PWD), headers=headers, data=data)


def serializer(record):
    last_scan = None if record.last_scan is None else record.last_scan.strftime(DATE_FORMAT)
    sched = record.sched.strftime(DATE_FORMAT)
    return {
            'id': record.id,
            'url': record.url,
            'username': record.username,
            'password': record.password,
            'sched': sched,
            'status': record.status,
            'last_scan': last_scan,
            }


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)