from flask import Flask, render_template, jsonify
import psutil
import os

# Inicializa a aplicação Flask
app = Flask(__name__)


def get_cpu_temperature():
    """
    Obtém a temperatura da CPU lendo o arquivo do sistema.
    Retorna a temperatura em graus Celsius.
    """
    try:
        # O caminho do arquivo de temperatura pode variar, mas este é o padrão para RPi
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        return f"{temp:.1f}°C"
    except FileNotFoundError:
        # Retorna uma mensagem de erro se o arquivo não for encontrado
        return "Não disponível"
    except Exception as e:
        # Captura outras exceções
        return f"Erro: {e}"


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


# Rota principal que renderiza a página HTML
@app.route('/')
def index():
    """Renderiza o template do dashboard."""
    return render_template('index.html')


# Rota da API que fornece os dados do sistema em formato JSON
@app.route('/stats')
def stats():
    """Coleta e retorna as estatísticas do sistema."""
    # Uso da CPU como porcentagem
    cpu_usage = psutil.cpu_percent(interval=1)

    # Informações de memória
    memory = psutil.virtual_memory()
    mem_total = format_bytes(memory.total)
    mem_used = format_bytes(memory.used)
    mem_percent = memory.percent

    # Informações de armazenamento (disco)
    disk = psutil.disk_usage('/')
    disk_total = format_bytes(disk.total)
    disk_used = format_bytes(disk.used)
    disk_percent = disk.percent

    # Monta o dicionário com todas as informações
    system_stats = {
        'cpu_temp': get_cpu_temperature(),
        'cpu_usage': cpu_usage,
        'mem_total': mem_total,
        'mem_used': mem_used,
        'mem_percent': mem_percent,
        'disk_total': disk_total,
        'disk_used': disk_used,
        'disk_percent': disk_percent,
    }

    # Retorna os dados como uma resposta JSON
    return jsonify(system_stats)


# Executa a aplicação
if __name__ == '__main__':
    # O host '0.0.0.0' torna o servidor acessível de fora do contêiner
    app.run(host='0.0.0.0', port=5000, debug=True)
