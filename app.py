# app.py
# Importa as bibliotecas necessárias
from flask import Flask, render_template, jsonify
import psutil
import os
import datetime
import time
import docker # Importação para comunicar com o Docker
from dateutil import parser # Para analisar datas do Docker

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- INICIALIZAÇÃO DO CLIENTE DOCKER ---
try:
    docker_client = docker.from_env()
    container_info_cache = {}
    CACHE_EXPIRATION = 10 # segundos
except docker.errors.DockerException:
    docker_client = None

# --- DEFINIÇÃO DOS LIMITES DE TEMPERATURA ---
TEMP_WARNING = 65.0
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
                if not ports: continue
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
    power = 1024; n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power; n += 1
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
            proc_name = 'N/A'; pid = conn.pid or 'N/A'
            try:
                if conn.pid:
                    p = psutil.Process(conn.pid)
                    proc_name = p.name()
                    if proc_name == 'docker-proxy':
                        container_name = get_container_name_from_port(port)
                        proc_name = f"Contêiner: {container_name}" if container_name else "Docker Proxy"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = 'Acesso Negado'
            listening_ports_map[port] = {'protocol': 'TCP' if conn.type == 1 else 'UDP', 'process': proc_name, 'pid': pid}
    return [{'port': port, **data} for port, data in listening_ports_map.items()]

def get_running_containers():
    """Obtém uma lista de contêineres em execução com detalhes."""
    if not docker_client: return []
    container_list = []
    try:
        for container in docker_client.containers.list():
            start_time = parser.isoparse(container.attrs['State']['StartedAt'])
            uptime_delta = datetime.datetime.now(start_time.tzinfo) - start_time
            container_list.append({
                'id': container.short_id, 'name': container.name,
                'image': container.image.tags[0] if container.image.tags else 'N/A',
                'status': container.status, 'uptime': str(uptime_delta).split('.')[0]
            })
    except Exception as e:
        print(f"Erro ao buscar contêineres: {e}"); return []
    return container_list

# Rota principal que renderiza a página HTML
@app.route('/')
def index():
    """Renderiza o template do dashboard."""
    return render_template('index.html')

# Rota da API que fornece os dados do sistema em formato JSON
@app.route('/stats')
def stats():
    disk_usage = psutil.disk_usage('/')

    hdd_mounted = is_hdd_mounted()

    # Se o HD estiver montado, pegamos as estatísticas dele.
    # Caso contrário, mostramos valores zerados.
    if hdd_mounted:
        hdd_usage = psutil.disk_usage('/mnt/media')
        hdd_status_text = "Conectado"
    else:
        # Cria um objeto 'falso' se o disco não estiver montado
        class MockUsage:
            total = 0;
            used = 0;
            percent = 0

        hdd_usage = MockUsage()
        hdd_status_text = "Ejetado / Desconectado"

    """Coleta e retorna as estatísticas do sistema."""
    # ... (coleta de dados igual à versão anterior)
    system_stats = {
        'cpu_temp': f"{get_cpu_temperature():.1f}°C" if get_cpu_temperature() is not None else "N/A",
        'cpu_temp_raw': get_cpu_temperature(),
        'cpu_usage': psutil.cpu_percent(interval=1),
        'temp_limits': {'warning': TEMP_WARNING, 'critical': TEMP_CRITICAL},
        'mem_total': format_bytes(psutil.virtual_memory().total),
        'mem_used': format_bytes(psutil.virtual_memory().used),
        'mem_percent': psutil.virtual_memory().percent,
        'disk_total': format_bytes(disk_usage.total),
        'disk_used': format_bytes(disk_usage.used),
        'disk_percent': disk_usage.percent,
        'hdd_status': hdd_status_text,
        'hdd_mounted': hdd_mounted,  # true ou false
        'hdd_total': format_bytes(hdd_usage.total),
        'hdd_used': format_bytes(hdd_usage.used),
        'hdd_percent': hdd_usage.percent,
        'swap_total': format_bytes(psutil.swap_memory().total),
        'swap_used': format_bytes(psutil.swap_memory().used),
        'swap_percent': psutil.swap_memory().percent,
        'net_sent': format_bytes(psutil.net_io_counters().bytes_sent),
        'net_recv': format_bytes(psutil.net_io_counters().bytes_recv),
        'load_avg': { 'min1': psutil.getloadavg()[0], 'min5': psutil.getloadavg()[1], 'min15': psutil.getloadavg()[2] },
        'processes': len(psutil.pids()),
        'uptime': get_uptime(),
        'listening_ports': get_listening_ports(),
        'running_containers': get_running_containers()
    }
    return jsonify(system_stats)

# --- ENDPOINTS ATUALIZADOS PARA USAR D-BUS ---
@app.route('/shutdown', methods=['POST'])
def shutdown_pi():
    """Desliga o Raspberry Pi enviando um comando D-Bus."""
    print("Recebido comando para desligar o sistema via D-Bus.")
    # Comando D-Bus para desligar
    os.system('dbus-send --system --print-reply --dest=org.freedesktop.login1 /org/freedesktop/login1 "org.freedesktop.login1.Manager.PowerOff" boolean:true')
    return jsonify({'status': 'success', 'message': 'Comando de desligamento enviado.'})

@app.route('/restart', methods=['POST'])
def restart_pi():
    """Reinicia o Raspberry Pi enviando um comando D-Bus."""
    print("Recebido comando para reiniciar o sistema via D-Bus.")
    # Comando D-Bus para reiniciar
    os.system('dbus-send --system --print-reply --dest=org.freedesktop.login1 /org/freedesktop/login1 "org.freedesktop.login1.Manager.Reboot" boolean:true')
    return jsonify({'status': 'success', 'message': 'Comando de reinicialização enviado.'})

# NOVO ENDPOINT PARA EJETAR O HD
@app.route('/eject-hdd', methods=['POST'])
def eject_hdd():
    """Para o container do Jellyfin e desmonta o HD externo."""
    print("Recebido comando para ejetar o HD externo.")

    # Comando para parar o Jellyfin
    stop_jellyfin_cmd = 'sudo /usr/bin/docker stop jellyfin'
    # Comando para desmontar o HD
    umount_hdd_cmd = 'sudo /bin/umount /mnt/media'

    try:
        print("Parando o container do Jellyfin...")
        os.system(stop_jellyfin_cmd)
        # Pequena pausa para garantir que o container parou
        time.sleep(5)

        print("Desmontando o HD em /mnt/media...")
        os.system(umount_hdd_cmd)

        print("HD ejetado com sucesso.")
        return jsonify({'status': 'success', 'message': 'HD ejetado com sucesso.'})

    except Exception as e:
        print(f"Erro ao ejetar o HD: {e}")
        return jsonify({'status': 'error', 'message': f'Erro ao ejetar HD: {e}'}), 500

# NOVO ENDPOINT PARA MONTAR O HD E INICIAR O JELLYFIN
@app.route('/mount-hdd', methods=['POST'])
def mount_hdd():
    """Monta o HD externo e inicia o container do Jellyfin."""
    print("Recebido comando para montar o HD e iniciar o Jellyfin.")

    mount_cmd = 'sudo /bin/mount /mnt/media'
    start_jellyfin_cmd = 'sudo /usr/bin/docker start jellyfin'

    try:
        print("Montando o HD em /mnt/media...")
        # Primeiro, tentamos montar o HD.
        os.system(mount_cmd)
        # Damos um tempo para o sistema de arquivos ficar pronto.
        time.sleep(3)

        print("Iniciando o container do Jellyfin...")
        # Em seguida, iniciamos o container que usa o HD.
        os.system(start_jellyfin_cmd)

        print("HD montado e serviço iniciado com sucesso.")
        return jsonify({'status': 'success', 'message': 'HD montado e Jellyfin iniciado.'})

    except Exception as e:
        print(f"Erro ao montar o HD: {e}")
        return jsonify({'status': 'error', 'message': f'Erro ao montar HD: {e}'}), 500

def is_hdd_mounted(mount_point='/mnt/media'):
    """Verifica se um ponto de montagem está ativo com logs de depuração detalhados."""
    proc_path = '/hostfs/proc/mounts'
    print("--- INICIANDO VERIFICAÇÃO DE MONTAGEM DE HD ---")
    print(f"DEBUG: Verificando a montagem em '{mount_point}' usando o arquivo '{proc_path}'")

    if not os.path.exists(proc_path):
        print(f"FALHA CRÍTICA: O arquivo '{proc_path}' NÃO EXISTE. Verifique se o volume '-v /:/hostfs:ro' está no comando 'docker run'.")
        return False

    try:
        with open(proc_path, 'r') as f:
            # Lê o conteúdo todo para os logs para podermos ver o que o container vê
            content = f.read()
            print("DEBUG: Conteúdo completo de /hostfs/proc/mounts:")
            # Adiciona bordas para facilitar a leitura nos logs
            print("=========================================")
            print(content)
            print("=========================================")

            # Itera sobre o conteúdo lido
            for line in content.splitlines():
                parts = line.split()
                if len(parts) > 1:
                    # Mostra cada ponto de montagem que ele encontra
                    print(f"DEBUG: Linha encontrada, ponto de montagem: '{parts[1]}'")
                    if parts[1] == mount_point:
                        print(f"SUCESSO: Correspondência encontrada para '{mount_point}'")
                        print("--- FIM DA VERIFICAÇÃO ---")
                        return True
    except Exception as e:
        print(f"ERRO INESPERADO: Ocorreu uma exceção ao ler o arquivo: {e}")
        print("--- FIM DA VERIFICAÇÃO COM ERRO ---")
        return False

    print(f"AVISO: Nenhuma correspondência para '{mount_point}' foi encontrada no arquivo.")
    print("--- FIM DA VERIFICAÇÃO ---")
    return False

# Executa a aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
