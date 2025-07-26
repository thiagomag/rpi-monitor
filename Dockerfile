# Dockerfile

# 1. Imagem base
# Usamos uma imagem Python slim, que é leve e ideal para o Raspberry Pi (arm64)
FROM python:3.9-slim

# 2. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Copia o arquivo de dependências
COPY requirements.txt .

# 4. Instala as dependências Python
# --no-cache-dir reduz o tamanho da imagem final
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o resto dos arquivos da aplicação para o diretório de trabalho
COPY . .

# 6. Expõe a porta que a aplicação Flask vai usar
EXPOSE 5000

# 7. Comando para iniciar a aplicação quando o contêiner for executado
CMD ["python", "app.py"]
