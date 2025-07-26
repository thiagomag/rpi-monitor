# app.py
# Importa as bibliotecas necessárias
from flask import Flask, render_template, jsonify
import psutil
import os
import datetime
import time

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- DEFINIÇÃO DOS LIMITES DE TEMPERATURA ---
# Você pode ajustar estes valores conforme sua necessidade
TEMP_WARNING = 65.0  # Temperatura em °C para alerta amarelo
TEMP_CRITICAL = 75.0  # Temperatura em °C para alerta vermelho


def get_cpu_temperature():
    """
    Obtém a temperatura da CPU como um número float.
    Retorna a temperatura em graus Celsius ou None se não for encontrada.
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
        return temp
    except (FileNotFoundError, ValueError):
        return None


def format_bytes(byte_count):
    """
    Formata uma quantidade de bytes para um formato legível (KB, MB, GB).
    """
    if byte_count is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}B"


def get_uptime():
    """Calcula o tempo de atividade do sistema e o formata."""
    boot_time_timestamp = psutil.boot_time()
    current_time_timestamp = time.time()
    uptime_seconds = current_time_timestamp - boot_time_timestamp
    return str(datetime.timedelta(seconds=int(uptime_seconds)))


def get_listening_ports():
    """
    Obtém uma lista de portas em escuta, com o processo associado.
    Nota: Esta operação pode ser um pouco lenta em sistemas com muitos processos.
    """
    connections = psutil.net_connections(kind='inet')
    listening_ports = []
    for conn in connections:
        if conn.status == 'LISTEN':
            proc_name = 'N/A'
            try:
                if conn.pid:
                    proc = psutil.Process(conn.pid)
                    proc_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = 'Acesso Negado'

            listening_ports.append({
                'port': conn.laddr.port,
                'protocol': 'TCP' if conn.type == 1 else 'UDP',
                'process': proc_name,
                'pid': conn.pid or 'N/A'
            })
    return listening_ports


# Rota principal que renderiza a página HTML
@app.route('/')
def index():
    """Renderiza o template do dashboard."""
    return render_template('index.html')


# Rota da API que fornece os dados do sistema em formato JSON
@app.route('/stats')
def stats():
    """Coleta e retorna as estatísticas do sistema."""
    # Métricas existentes
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_temp_raw = get_cpu_temperature()

    # --- Novas Métricas ---
    swap = psutil.swap_memory()
    net_io = psutil.net_io_counters()
    load_avg = psutil.getloadavg()
    uptime = get_uptime()
    processes = len(psutil.pids())
    listening_ports = get_listening_ports()

    system_stats = {
        # Métricas de CPU e Temperatura
        'cpu_temp': f"{cpu_temp_raw:.1f}°C" if cpu_temp_raw is not None else "N/A",
        'cpu_temp_raw': cpu_temp_raw,
        'cpu_usage': cpu_usage,
        'temp_limits': {'warning': TEMP_WARNING, 'critical': TEMP_CRITICAL},

        # Métricas de Memória
        'mem_total': format_bytes(memory.total),
        'mem_used': format_bytes(memory.used),
        'mem_percent': memory.percent,

        # Métricas de Disco
        'disk_total': format_bytes(disk.total),
        'disk_used': format_bytes(disk.used),
        'disk_percent': disk.percent,

        # --- Novos Dados no JSON ---
        # Memória Swap
        'swap_total': format_bytes(swap.total),
        'swap_used': format_bytes(swap.used),
        'swap_percent': swap.percent,

        # Rede
        'net_sent': format_bytes(net_io.bytes_sent),
        'net_recv': format_bytes(net_io.bytes_recv),

        # Carga do Sistema e Processos
        'load_avg': {'min1': load_avg[0], 'min5': load_avg[1], 'min15': load_avg[2]},
        'processes': processes,
        'uptime': uptime,

        # Portas
        'listening_ports': listening_ports
    }

    return jsonify(system_stats)


# Executa a aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
