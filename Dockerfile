# Dockerfile

# 1. Imagem base
# Usamos uma imagem Python slim, que é leve e ideal para o Raspberry Pi (arm64)
FROM python:3.9-slim

# --- NOVO PASSO: Instalar o pacote 'dbus' ---
# Atualiza a lista de pacotes e instala o dbus sem instalar pacotes recomendados (para manter a imagem pequena)
# Depois, limpa o cache do apt para reduzir o tamanho final da imagem.
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli util-linux dbus && \
    rm -rf /var/lib/apt/lists/*
# 2. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Copia o arquivo de dependências
COPY requirements.txt .

# 4. Instala as dependências Python
# --no-cache-dir reduz o tamanho da imagem final
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o resto dos arquivos da aplicação para o diretório de trabalho
COPY . .

# 6. Expõe a porta que a aplicação Flask vai usar (informativo, pois usamos --net=host)
EXPOSE 5000

# 7. Comando para iniciar a aplicação quando o contêiner for executado
CMD ["python", "app.py"]