import json
import io
from flask import Flask, send_file, request, Response
from prometheus_client import start_http_server, Counter, generate_latest, Gauge
import subprocess

app = Flask(__name__)

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
MBFACTOR = float(1 << 20)
memory_gauge = Gauge(
    'memory_usage_in_mb',
    'Amount of memory in megabytes currently in use by this user.',
    ['username']
)

cpu_gauge_user = Gauge(
    'user_cpu_usage_in_jiffies',
    'Amount of time this user has used the CPU in jiffies.',
    ['username']
)

cpu_gauge_system = Gauge(
    'system_cpu_usage_in_jiffies',
    'Amount of time this user has used the system CPU in jiffies.',
    ['username']
)

@app.route('/data', methods=['GET'])
def get_data():
    """Returns all data."""
    data = subprocess.check_output("./metrics.sh")
    data = str(data, 'utf-8')
    data_list = data.splitlines()
    for item in data_list:
        print("type is {}".format(type(item)))
        attributes = str(item).split(';')
        memory = int(attributes[0])/MBFACTOR
        user_cpu = attributes[1]
        system_cpu = attributes[2]
        username = attributes[3]
        # timestamp = attributes[4]
        # container = attributes[5]
        memory_gauge.labels(username).set(memory)
        cpu_gauge_user.labels(username).set(user_cpu)
        cpu_gauge_system.labels(username).set(system_cpu)

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
