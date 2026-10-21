---
name: upscale-natural
description: Amplie imagens locais para impressão com Expandia, mistura natural Real-ESRGAN/Lanczos de 20% ou 30%, diagnóstico do computador e processamento em lote. Use também para instalar ou diagnosticar esta ferramenta local no Windows ou Mac.
---

# Expandia

Execute os scripts desta skill localmente. O motor não usa API paga.
O padrão aprovado é **20% Real-ESRGAN x4plus + 80% Lanczos com nitidez
moderada**. Ofereça 30% quando o usuário pedir mais definição. Misturar
não elimina a reconstrução de detalhes do modelo. Não aplique GFPGAN,
reconstrução facial ou nova nitidez após a mistura.

## Instalação e diagnóstico

Os comandos abaixo são relativos à raiz do repositório. Resolva o caminho
da skill se estiver trabalhando a partir de uma instalação do plugin.

1. Execute `python3 plugins/expandia/skills/upscale-natural/scripts/doctor.py`.
   No Windows, `python` é aceito. Isso funciona sem instalar bibliotecas.
2. Execute `python3 plugins/expandia/skills/upscale-natural/scripts/setup.py`.
   Cria ambiente isolado em `runtime/`, instala versões fixadas e baixa
   somente pesos oficiais com verificação SHA256. Não muda o Python global.
3. Use o Python de `runtime/.venv/bin/python` no Mac ou
   `runtime/.venv/Scripts/python.exe` no Windows para os próximos comandos.
4. Execute `scripts/expandia.py benchmark`. Meça primeiro o desempenho local.

Aceita Python 3.9 a 3.12, macOS 11+ Intel/Apple Silicon ou Windows 10/11
64 bits. Se houver incompatibilidade, relate o diagnóstico e resolva a
dependência; não substitua silenciosamente por outro motor. A instalação
usa wheels prontos, sem tentar compilar dependências no computador.

## Uso

Com o Python do ambiente isolado, execute:

```text
scripts/expandia.py plan CAMINHO --scale 4 --ppi 300
scripts/expandia.py upscale CAMINHO --scale 4 --ppi 300 --strength 20
scripts/expandia.py upscale CAMINHO --scale 4 --ppi 300 --strength 30
scripts/expandia.py batch PASTA --scale 4 --ppi 300 --strength 20
```

`CAMINHO` e `PASTA` devem ser caminhos locais reais. Aceita espaços e
acentos quando os argumentos são passados corretamente. Não procure
credenciais nem presuma acesso a arquivos de outro computador.
Use `--output-dir PASTA` se o usuário especificar destino diferente.
Por padrão, salva ao lado do original, com sufixo identificando escala,
PPI e proporção. Preserva originais e não sobrescreve saídas diferentes.
Lotes ignoram resultados Expandia anteriores, vetores e fontes; os SVGs
já são escaláveis. O lote é sequencial e retoma resultados verificados.

`plan` calcula dimensões e verifica limites antes de processar. O limite
de saída e o tamanho dos blocos são ajustados à RAM detectada, com teto
de 64 MP para computadores com pelo menos 32 GiB de RAM (até três horas por imagem). A proporção e o fator solicitados nunca são reduzidos para
caber: se excederem os limites, explique e proponha 2× ou uma imagem menor.
PPI é metadado de impressão, não fator de ampliação.

O código usa CPU deliberadamente. Não prometa desempenho perfeito nem
aceleração GPU automática. O diagnóstico identifica macOS/arquitetura/RAM
e preserva a mesma combinação visual; a calibração só altera parâmetros
de execução. O modo 2× usa o modelo nativo 4× e reduz o bloco a 2×.

## Trabalhos demorados

Estime com o benchmark, explicando que o conteúdo e o contexto dos blocos
afetam o tempo. `batch` salva `expandia-lote.json` na pasta de destino
antes do processamento e o atualiza entre blocos. Pode continuar em outro
terminal/processo local quando o usuário autorizar a execução em segundo
plano. Evite iniciar duplicatas: o script usa trava de execução.
Para interromper, use Ctrl+C ou crie `PARAR-EXPANDIA.txt` na pasta de saída;
para retomar, remova esse marcador e repita o comando. Não afirme que o
lote terminou antes de verificar o relatório e os arquivos.

Não transfira o `.venv` do Windows para o Mac. Transfira o repositório ou ZIP
e configure um ambiente próprio em cada máquina. A configuração e os
relatórios locais ficam em `runtime/` e não devem ser versionados.
