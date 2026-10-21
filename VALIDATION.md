# Validação da versão 0.1.0

- Configuração completa executada em Windows x64, Python 3.12, em ambiente
  novo e isolado: dependências nas versões fixadas, pesos oficiais com hashes
  conferidos, inferência, mistura de 20%, gravação de PNG/300 PPI e benchmark.
- Modelos foram baixados do release oficial durante a instalação.
- Pacotes Python foram fornecidos por wheels oficiais do PyPI em um cache
  local de teste. A disponibilidade dos mesmos wheels para Mac Intel e
  Apple Silicon foi conferida, mas sua execução no Mac ainda não foi testada.
- Quatro testes automatizados passaram: perfis por memória; diagnóstico de
  Mac Intel com dados simulados; proporção, dimensões, PPI e retomada de
  saída verificada; limite de saída e cancelamento.
- Verificado que origem alterada não sobrescreve resultado anterior.
- Formato do plugin, skill e marketplace inclui execução local e não requer
  MCP/API. A descoberta e instalação na interface do aplicativo de destino
  ainda precisam ser validadas; a skill pode ser usada diretamente no projeto.

Não há aprovação de compatibilidade real com o iMac específico antes de
executar `iniciar.py` nele. Benchmarks sintéticos são estimativas, não SLA.
