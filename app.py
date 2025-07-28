# app.py
# Importa as bibliotecas necessárias
from flask import Flask, render_template, jsonify
import psutil
import os
import datetime
import time
import docker  # Importação para comunicar com o Docker
from dateutil import parser  # Para analisar datas do Docker

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- INICIALIZAÇÃO DO CLIENTE DOCKER ---
try:
    docker_client = docker.from_env()
    container_info_cache = {}
    CACHE_EXPIRATION = 10  # segundos
except docker.errors.DockerException:
    docker_client = None

# --- DEFINIÇÃO DOS LIMITES DE TEMPERATURA ---
TEMP_WARNING = 70.0
TEMP_CRITICAL = 75.0


def get_container_name_from_port(port):
    """Verifica qual contêiner está expondo uma determinada porta."""
    global container_info_cache
    if not docker_client:
        return None

    now = time.time()
    if 'timestamp' not in container_info_cache or (now - container_info_cache['timestamp']) >= CACHE_EXPIRATION:
        container_info_cache = {'timestamp': now}
        try:
            for container in docker_client.containers.list():
                ports = container.attrs.get('HostConfig', {}).get('PortBindings')
                if not ports:
                    continue
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            host_port_str = binding.get('HostPort')
                            if host_port_str:
                                container_info_cache[int(host_port_str)] = container.name
        except Exception:
            pass
    return container_info_cache.get(port)


def get_cpu_temperature():
    """Obtém a temperatura da CPU."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
        return temp
    except (FileNotFoundError, ValueError):
        return None


def format_bytes(byte_count):
    """Formata bytes em um formato legível."""
    if byte_count is None: return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}B"


def get_uptime():
    """Calcula o tempo de atividade do sistema."""
    return str(datetime.timedelta(seconds=int(time.time() - psutil.boot_time())))


def get_listening_ports():
    """Obtém uma lista de portas em escuta."""
    connections = psutil.net_connections(kind='inet')
    listening_ports_map = {}
    for conn in connections:
        if conn.status == 'LISTEN':
            port = conn.laddr.port
            if port in listening_ports_map: continue
            proc_name = 'N/A'
            pid = conn.pid or 'N/A'
            try:
                if conn.pid:
                    p = psutil.Process(conn.pid)
                    proc_name = p.name()
                    if proc_name == 'docker-proxy':
                        container_name = get_container_name_from_port(port)
                        proc_name = f"Contêiner: {container_name}" if container_name else "Docker Proxy"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = 'Acesso Negado'
            listening_ports_map[port] = {'protocol': 'TCP' if conn.type == 1 else 'UDP', 'process': proc_name,
                                         'pid': pid}
    return [{'port': port, **data} for port, data in listening_ports_map.items()]


def get_running_containers():
    """
    Obtém uma lista de contêineres em execução com detalhes.
    """
    if not docker_client:
        return []

    container_list = []
    try:
        for container in docker_client.containers.list():
            start_time_str = container.attrs['State']['StartedAt']
            start_time = parser.isoparse(start_time_str)
            # Converte para um objeto de tempo "aware" do fuso horário local para fazer a subtração correta
            uptime_delta = datetime.datetime.now(start_time.tzinfo) - start_time

            container_list.append({
                'id': container.short_id,
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else 'N/A',
                'status': container.status,
                'uptime': str(uptime_delta).split('.')[0]  # Remove os microssegundos
            })
    except Exception as e:
        # Se houver um erro (ex: comunicação com o Docker), retorna uma lista vazia
        print(f"Erro ao buscar contêineres: {e}")
        return []
    return container_list


# Rota principal que renderiza a página HTML
@app.route('/')
def index():
    """Renderiza o template do dashboard."""
    return render_template('index.html')


# Rota da API que fornece os dados do sistema em formato JSON
@app.route('/stats')
def stats():
    """Coleta e retorna as estatísticas do sistema."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_temp_raw = get_cpu_temperature()
    swap = psutil.swap_memory()
    net_io = psutil.net_io_counters()
    load_avg = psutil.getloadavg()

    system_stats = {
        'cpu_temp': f"{cpu_temp_raw:.1f}°C" if cpu_temp_raw is not None else "N/A",
        'cpu_temp_raw': cpu_temp_raw,
        'cpu_usage': cpu_usage,
        'temp_limits': {'warning': TEMP_WARNING, 'critical': TEMP_CRITICAL},
        'mem_total': format_bytes(memory.total),
        'mem_used': format_bytes(memory.used),
        'mem_percent': memory.percent,
        'disk_total': format_bytes(disk.total),
        'disk_used': format_bytes(disk.used),
        'disk_percent': disk.percent,
        'swap_total': format_bytes(swap.total),
        'swap_used': format_bytes(swap.used),
        'swap_percent': swap.percent,
        'net_sent': format_bytes(net_io.bytes_sent),
        'net_recv': format_bytes(net_io.bytes_recv),
        'load_avg': {'min1': load_avg[0], 'min5': load_avg[1], 'min15': load_avg[2]},
        'processes': len(psutil.pids()),
        'uptime': get_uptime(),
        'listening_ports': get_listening_ports(),
        'running_containers': get_running_containers()  # --- NOVA INFORMAÇÃO ---
    }

    return jsonify(system_stats)


# Executa a aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
