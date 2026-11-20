# Plano de melhorias do Orveta

## Mapa do projeto

- `app.py`: ponto de entrada e imports de compatibilidade; `orveta_ui.py`: interface Tkinter e coordenação da fila.
- `download_options.py` e `media_commands.py`: argumentos de download, conversão e classificação de erros.
- `process_runner.py`: execução de subprocessos e envio de eventos; `settings_store.py`: persistência JSON.
- `diagnostics.py`: logs rotativos; `test_characterization.py`: testes de caracterização.
- `updater.py`: decisão da ação de atualização manual existente; a atualização verificada pertence à fase 2.
- `translations.py`: traduções e conversão entre rótulos exibidos e valores originais.
- `test_converter.py` e `test_formats.py`: testes existentes de conversão, fila e formatos.
- `installer.iss`: instalador Inno Setup por usuário; AppId deve permanecer `{7A3CFE70-BD45-47CF-8182-4D784F985C1E}`.
- `Orveta.spec`, `orveta.ico`, `requirements.txt` e `README.md`: build, identidade e documentação.
- `.venv/`, `vendor/`, `build/`, `dist/` e `release/`: dependências locais e arquivos gerados, ignorados pelo Git.

## Ordem

1. Registrar linha de base, caracterizar comportamento e separar responsabilidades; registrar diagnóstico e persistência segura.
2. Avaliar runtimes JavaScript, atualizações verificadas e mensagens; implementar cookies opcionais por último e em commit próprio.
3. Corrigir navegação e fluxo de download, ícone, contraste e internacionalização.
4. Preparar build reproduzível onedir, avaliar binários FFmpeg e assinaturas opcionais; preservar a instalação anterior.
5. Documentar licenças e instruções de teste manual, incluindo instalação limpa e atualização.

Cada fase deve ser testada, aberta e registrada em commit separado. Não serão adicionadas dependências pesadas sem avaliação documentada. Não se presume que a interface foi validada visualmente ou que o instalador foi testado em máquina limpa.

## Linha de base

- Repositório Git: inexistente no início do trabalho; será inicializado sem incluir binários ignorados.
- FFmpeg: executável 170.074.624 bytes; ffprobe: 169.858.048 bytes, compilação GPL estática.
- Instalador 0.8.0: 133.342.039 bytes.
- PyInstaller atual: onefile; medição de tempo de abertura e comparação com onedir pendentes.
- `pytest` não estava instalado no ambiente existente.
- `pytest` instalado no ambiente local e descrito em `requirements-dev.txt`; os testes de caracterização identificaram um erro preexistente na classificação de formato indisponível.
- Skillpedia: MCP não encontrado na sessão; nenhuma skill correspondente foi encontrada no projeto.

## Avaliação inicial do runtime JS

A [documentação EJS do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS) lista Deno, Node e QuickJS; Deno é habilitado por padrão, Node e QuickJS exigem `--js-runtimes`. Deno anunciou o encerramento do desenvolvimento do runtime após o período informado no [anúncio oficial](https://deno.com/blog/cloudflare). A escolha ainda depende de verificar tamanho dos binários Windows, licenças, versão mínima e compatibilidade com a release exata distribuída. Nenhum runtime foi incluído ainda.

QuickJS-NG usa [licença MIT](https://github.com/quickjs-ng/quickjs/blob/v0.18.0/LICENSE); o guia EJS aceita QuickJS-NG, mas alerta sobre arquivos temporários e recomenda versão 0.12.0 ou posterior para desempenho. A release 0.18.0 lista executáveis para Windows, mas tamanho, integridade e execução do binário específico ainda não foram verificados. Node requer versão 22 ou posterior segundo o guia atual; tamanho e licença da distribuição exata ainda precisam ser medidos. O projeto Deno recomenda seu runtime no EJS, porém seu mantenedor anunciou o término do desenvolvimento. A seleção final deve comparar os binários obtidos, não apenas os nomes dos projetos.

O candidato QuickJS-NG 0.18.0 Windows x64 foi obtido da release oficial: 1.873.152 bytes, SHA-256 `ff03398d74ea6e6bd3a8e58058f7003225abcac229d7d57775b7aaae812a49c7`, correspondente ao publicado na release; executou `console.log(1+1)`. O instalador inclui o binário e sua licença, e o app passa seu caminho via `--js-runtimes`. Ainda faltam medir Node e Deno e validar extração real do YouTube, portanto a escolha permanece provisória.

## Estado

- [ ] Fase 1
- [ ] Fase 2 (cookies em commit separado)
- [ ] Fase 3
- [ ] Fase 4
- [ ] Fase 5

### Trabalho posterior em andamento

- QuickJS-NG 0.18.0 x64: 1.873.152 bytes, hash verificado e teste simples executado. A análise de metadados de um vídeo público do YouTube pelo processo de desenvolvimento retornou título com sucesso; download real, ausência do runtime e testes em máquinas limpas continuam pendentes.
- Atualizador: código de teste verifica checksum, execução e substituição com restauração; os testes simulam falhas, mas não houve teste de atualização real nem validação de assinatura criptográfica dos checksums.
- PyInstaller onedir de teste: aproximadamente 27,6 MB (somente app e `_internal`); o instalador de teste teve 92.139.933 bytes, contra 133.342.039 bytes na versão 0.8.0. Uma única medição local de criação da janela com `measure_startup.py`: onefile 0,802 s e onedir 0,395 s; outra compilação onedir marcou 0,599 s. São medições pontuais em uma máquina, não uma garantia de desempenho nem tempo até uma operação ficar pronta.
- FFmpeg: o app usa `libx264`, `libvpx-vp9`, AAC, `libmp3lame`, `libopus`, FLAC e PCM; um build LGPL precisa ser avaliado contra a ausência potencial dos codecs GPL, especialmente x264. Foi escolhido para teste o build GPL compartilhado da linha 8.1, identificado como `n8.1.3-36-ge22a4510c9-20261119`, com os codecs acima verificados. O ZIP teve SHA-256 `6345aa50f6067213fb3fec347025ad8dbd99a86b8f14e5f20c6561e868f5be8e`, correspondente ao checksum oficial consultado no download. Os dois executáveis e DLLs somam 202.449.920 bytes, contra 339.932.672 bytes dos dois executáveis anteriores. `ffprobe` foi mantido, pois é utilizado pelo yt-dlp/FFmpeg nos fluxos de pós-processamento.
- Assinatura opcional configurada por variáveis de ambiente, mas não testada por ausência de certificado. Licenças e correspondência de fontes ainda requerem revisão antes de distribuição.
- Contraste calculado a partir dos tokens: texto auxiliar `#5A6B62` em `#FAF8F5` = 5,33:1; botão secundário desabilitado `#4C5E53` em `#E2DDD6` = 5,13:1; botão principal desabilitado branco em `#51695B` = 5,96:1. O contraste efetivamente renderizado e estados de foco ainda precisam de inspeção manual em DPI alto.
- Interface: fila movida ao lado de Baixar; rótulos, limpeza de seleção, ícone, foco, exemplo de link, análise ao colar/Enter, formato e qualidade lado a lado e botão para abrir pasta foram implementados. Exibição condicional de opções conforme o conteúdo analisado, drag-and-drop e revisão integral de tradução ainda estão pendentes. O teste em sessão gráfica somente confirmou inicialização; não houve aprovação visual.
- `THIRD_PARTY_NOTICES.md`, licenças copiadas ao instalador e tela Sobre foram acrescentados; é necessário verificar fontes e obrigações completas de cada binário e de futuras atualizações. `capture_ui.ps1` e `measure_startup.py` são parametrizados para testes locais.

### Fase 1 em andamento

Caracterização adicionada para URL, argumentos de download, erros, conversão e JSON. Conversão e mensagens foram movidas para `media_commands.py`, persistência para `settings_store.py`, montagem dos argumentos para `download_options.py`, execução para `process_runner.py`, interface para `orveta_ui.py` e decisão da atualização manual para `updater.py`, preservando os imports existentes. JSON usa arquivos temporários exclusivos e substituição atômica. Logs limitados e diagnóstico inicial foram adicionados sem registrar URLs, caminhos nem cookies. A fase ainda precisa de revisão integrada. O repositório foi inicializado e a linha de base preparada no índice; o commit aguarda identidade Git. Nada deve ser enviado ao GitHub.
