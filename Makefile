# Makefile para gerenciar o contêiner de monitoramento do Raspberry Pi

# --- Variáveis Configuráveis ---
# Altere aqui se quiser usar um nome de imagem ou contêiner diferente.
IMAGE_NAME := thiagomag/rpi-monitor
CONTAINER_NAME := rpi-monitor-app

# --- Alvos Principais ---

# O alvo padrão. Executar `make` ou `make all` irá reconstruir e reiniciar tudo.
all: rebuild

# Constrói a imagem Docker a partir do Dockerfile local.
build:
	@echo "--> Construindo a imagem Docker: $(IMAGE_NAME):latest..."
	@docker build -t $(IMAGE_NAME):latest .

# Para o contêiner em execução. O hífen no início ignora o erro se o contêiner não existir.
stop:
	@echo "--> Parando o contêiner $(CONTAINER_NAME)..."
	@-docker stop $(CONTAINER_NAME)

# Remove o contêiner. Depende de 'stop' para garantir que ele seja parado primeiro.
rm: stop
	@echo "--> Removendo o contêiner $(CONTAINER_NAME)..."
	@-docker rm $(CONTAINER_NAME)

# Executa o contêiner com todas as configurações necessárias.
run:
	@echo "--> Iniciando o contêiner $(CONTAINER_NAME)..."
	@docker run -d \
	--name $(CONTAINER_NAME) \
	--restart unless-stopped \
	--privileged \
	--net="host" \
	--pid="host" \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v /var/run/dbus:/var/run/dbus \
	$(IMAGE_NAME):latest

# Reinicia o contêiner (para, remove e executa novamente).
restart: rm run
	@echo "--> Contêiner reiniciado com sucesso!"

# Reconstrói a imagem e reinicia o contêiner. Ideal para aplicar mudanças no código.
rebuild: build restart
	@echo "--> Imagem reconstruída e contêiner reiniciado com sucesso!"

# Este alvo é um alias para 'rebuild', juntando todos os passos em um único comando.
deploy: rebuild
	@echo "--> Deploy completo!"


# --- Alvos Auxiliares ---

# Mostra os logs do contêiner em tempo real.
logs:
	@echo "--> Mostrando logs de $(CONTAINER_NAME)... (Pressione Ctrl+C para sair)"
	@docker logs -f $(CONTAINER_NAME)

# Envia a imagem mais recente para o Docker Hub.
push: build
	@echo "--> Enviando imagem $(IMAGE_NAME):latest para o Docker Hub..."
	@docker push $(IMAGE_NAME):latest

# Limpa o ambiente parando e removendo o contêiner.
clean: rm
	@echo "--> Ambiente limpo."


# Declara que os alvos não são arquivos, o que é uma boa prática.
.PHONY: all build stop rm run restart rebuild deploy logs push clean