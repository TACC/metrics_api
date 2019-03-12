from flask import Flask, send_file, request, Response
from prometheus_client import start_http_server, Counter, generate_latest, Gauge
import docker
import logging

logger = logging.getLogger(__name__)

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
worker_mem_free = Gauge(
    'mem_free_for_this_worker_in_gb',
    'Amount of memory free for this worker in GB',
)

users_per_worker = Gauge(
    'number_of_users_on_this_worker',
    'The number of users with notebook servers on this worker.'
)

client = docker.from_env(version='1.23')


@app.route('/data', methods=['GET'])
def get_data():
    """Returns all data."""
    containers = client.containers.list(filters={'name':'jupyter-'})
    users_per_worker.set(len(containers))
    for container in containers:
        username = container.name
        try:
            with open('/docker/memory/{}/memory.usage_in_bytes'.format(container.id), 'r') as memfile:
                memory = memfile.read()
                memory = int(memory) / MBFACTOR
                memory_gauge.labels(username).set(memory)
        except Exception as e:
            logger.error("Failed to update memory metric. Exception: {}".format(e))

        try:
            with open('/docker/cpu/{}/cpuacct.stat'.format(container.id), 'r') as cpufile:
                user_cpu_line = cpufile.readline().split()
                user_cpu = user_cpu_line[1]
                cpu_gauge_user.labels(username).set(str(user_cpu))
                system_cpu_line = cpufile.readline().split()
                system_cpu = system_cpu_line[1]
                cpu_gauge_system.labels(username).set(str(system_cpu))
        except Exception as e:
            logger.error("failed to update CPU metrics. Exception: {}".format(e))
    try:
        with open('/worker/meminfo') as workerfile:
            total_mem_line = workerfile.readline().split()
            total_mem = total_mem_line[1]
            free_mem_line = workerfile.readline().split()
            free_mem = int(free_mem_line[1]) / MBFACTOR
            worker_mem_free.set(free_mem)
    except Exception as e:
        logger.error("Failed to update worker metrics. Exception: {}".format(e))

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
