# Expandia

Upscale pessoal local para impressão. Padrão aprovado: **20% Real-ESRGAN
x4plus + 80% Lanczos com nitidez moderada**. Opção de 30% disponível.
Sem API paga, sem envio das imagens a servidores, sem reconstrução facial
GFPGAN. Há reconstrução de texturas pelo Real-ESRGAN; a mistura reduz sua
influência, não garante preservação exata de detalhes.

## Como usar no iMac ou em outro computador pelo Codex

No aplicativo ChatGPT, em uma conversa do **modo Codex local**, peça:

> Baixe o repositório público https://github.com/nandaota/expandia, leia
> AGENTS.md e configure o Expandia neste computador executando iniciar.py.
> Faça o diagnóstico automático, prepare as dependências, verifique o
> modelo, rode o teste e o benchmark e me diga quando estiver pronto.

O repositório é público: qualquer pessoa pode clonar ou baixar o ZIP, sem
precisar de convite ou autenticação no GitHub. Não são necessárias chaves
de API de IA. Cada computador cria seu próprio ambiente local.

Depois da configuração, peça, por exemplo:

> Use o Expandia para ampliar as imagens desta pasta em 4×, a 300 PPI,
> com nosso padrão de 20%, salvando ao lado dos originais.

Ou: “Nesta imagem use 30%”. Os originais são preservados.

### Procedimento para o Codex configurar automaticamente

1. Identifique um Python 3.9–3.12 disponível no computador. O runtime
   fornecido pelo aplicativo pode ser usado se for compatível. Se não houver,
   instale Python 3.12 pelo canal oficial usando a autorização e as permissões
   disponíveis; se houver autenticação ou permissão obrigatória, explique o
   ponto exato. Não use sudo sem necessidade e não modifique o Python do sistema.
2. Execute `<python compatível> iniciar.py` na raiz deste repositório.
   Esse comando faz diagnóstico, ambiente isolado, dependências, download de
   modelos, verificação SHA256, inferência de teste e benchmark.
3. Confira `plugins/expandia/skills/upscale-natural/runtime/installation.json`,
   `hardware.json` e `benchmark.json`. Não afirme que está pronto se os testes
   não passaram. A instalação não processa fotos pessoais automaticamente.
4. A skill está em `plugins/expandia/skills/upscale-natural/SKILL.md`.
   Use-a diretamente no projeto ou instale o plugin a partir da fonte local
   **Expandia pessoal** no diretório de plugins e reinicie o aplicativo se
   necessário. O marketplace do projeto já está em `.agents/plugins/`.
   Se a interface da conta não mostrar plugins locais, use a skill dentro
   do projeto; não prometa instalação global que não foi verificada.

## O que é ajustado automaticamente

- Windows/macOS, Intel x86_64/AMD64 ou Apple Silicon arm64.
- CPU, núcleos disponíveis, memória RAM e versão do Python/sistema.
- Quantidade de threads, tamanho dos blocos e limite de pixels de saída.
- Benchmark local para estimar duração. CPU é o modo inicial conservador.
- Tentativa com blocos menores em caso de `MemoryError` capturável.

O motor e a mistura visual permanecem os mesmos. Não há promessa de
funcionamento perfeito em todo hardware. Falhas nativas, pouca memória,
sistema antigo ou políticas da máquina podem exigir intervenção. GPU/Metal
não são ativados automaticamente nesta versão.

Requisitos: **Python 3.9–3.12, macOS 11+ ou Windows 10/11 de 64 bits**.
Mac Intel e Apple Silicon têm pacotes NCNN próprios. Instalação, inferência de teste e benchmark foram verificados também em
macOS Intel. O tempo de processamento depende do computador.
Internet é usada para obter código, bibliotecas e modelo na configuração.
Após instalada, a ampliação é local. O chat continua sujeito ao seu plano.

## Inicialização manual

```sh
python3 iniciar.py
```

Ou use `bash Instalar-no-Mac.command` no Mac e `Instalar-no-Windows.cmd`
no Windows. Para diagnóstico sem instalar dependências:

```sh
python3 iniciar.py --diagnostic-only
```

Não copie o `.venv` de um computador para outro: cada instalação cria seu
próprio ambiente em `runtime/`. Um ZIP deste repositório também serve.

## Formatos e limites

PNG, JPG, TIFF e WebP estáticos, RGB/cinza de 8 bits; transparência, CMYK,
16 bits e arquivos multipágina ainda não são aceitos. Vetores SVG e fontes
não entram em lotes de upscale. Saída PNG, 2× ou 4×, 150 ou 300 PPI.
20% por padrão, 30% quando solicitado. Teto absoluto de 64 MP em computadores com 32 GiB de RAM ou mais, reduzido
em computadores com menos RAM. Perfis de 64 MP permitem até três horas por imagem. Não reduz automaticamente a escala pedida.

Saídas usam o final `_expandia4x_300ppi_RE20.png` (ou configuração equivalente).
Lotes são sequenciais, com relatório `expandia-lote.json` e retomada por arquivo.
Ctrl+C ou `PARAR-EXPANDIA.txt` no destino interrompem o trabalho; remova o
marcador e repita o comando para retomar. O computador deve permanecer ligado.
O programa tenta evitar suspensão por inatividade durante a execução.

## Dependências e licenças

Pesos oficiais do [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN),
executados pelo [NCNN](https://github.com/Tencent/ncnn). O instalador extrai
apenas `.bin` e `.param` do ZIP oficial, que é rotulado como Windows; os pesos
são portáveis e nenhum executável Windows é usado no Mac.

Versões: NumPy 1.26.4, Pillow 10.4.0, OpenCV headless 4.8.1.78,
NCNN 1.0.20250503. As licenças do modelo/runtime estão em `THIRD_PARTY/`.
Não inclui arquivos de imagem pessoais, chaves, diagnósticos de máquinas ou
ambientes locais. Os modelos são baixados na configuração, com hashes fixados.
