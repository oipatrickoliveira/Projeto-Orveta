# Orveta — Baixar vídeos

Versão local para uso pessoal. O instalador Windows é gerado em `release/` pelo script de build e inclui o aplicativo, yt-dlp, FFmpeg e runtime JavaScript. Aceita links HTTP(S) de sites compatíveis com o yt-dlp, incluindo vídeos de redes sociais. A disponibilidade varia por vídeo e plataforma; conteúdo com DRM não é suportado. Baixe apenas conteúdo para o qual você tenha autorização.

Para atualizar o aplicativo, execute o novo instalador usando a mesma conta do Windows. Ele reutiliza a pasta e as opções anteriores e substitui os arquivos do programa; não é necessário desinstalar primeiro. Feche o Orveta antes de atualizar. Os vídeos baixados não são removidos. O aplicativo ainda não procura novas versões do próprio Orveta; em erros de extração específicos, tenta atualizar o mecanismo yt-dlp e repetir o download uma vez.

Formatos disponíveis: vídeo MP4, MKV e WebM; áudio MP3, M4A, Opus, WAV e FLAC. A qualidade de vídeo pode ser limitada a 1080p, 720p ou 480p, quando disponível. A conversão pode demorar e não melhora a qualidade do conteúdo original.

Na aba **Converter arquivos**, escolha um vídeo ou áudio do computador, selecione o formato e indique onde salvar o resultado. É possível extrair o áudio de um vídeo escolhendo um formato de áudio. O arquivo original não é alterado; o nome de saída precisa ser novo. Uma conversão cancelada ou que falhe pode deixar um arquivo parcial.

O seletor no topo permite testar português, inglês e espanhol. As traduções estão em desenvolvimento; algumas mensagens e detalhes técnicos continuam em português ou no idioma das ferramentas. A pasta de destino, as opções de formato, a qualidade e o idioma são salvos no perfil do Windows, junto com o histórico de até 500 operações concluídas. O histórico mostra caminhos locais e permite abrir a pasta de destino.

A fila processa downloads adicionados e conversões em lote sequencialmente enquanto o programa estiver aberto. Para conversão em lote, selecione os arquivos e a pasta de destino: se algum nome já existir, o lote não é iniciado. O corte opcional usa tempos em segundos e gera um arquivo novo. Na aba Legendas é possível pedir arquivos separados ou incorporados a MP4/MKV, quando disponíveis no site. A aba Fila também oferece a atualização manual do yt-dlp; a disponibilidade depende da rede e do serviço de origem. Os novos controles ainda não estão totalmente traduzidos.

Na aba Opções é possível escolher baixar os primeiros 100 itens de uma playlist e limitar a velocidade com valores como `500K` ou `2M` bytes por segundo. Por padrão, apenas o vídeo individual é baixado. Na aba de download há um botão para colar o link da área de transferência. O histórico registra o último arquivo de uma playlist concluída; itens individuais ainda não são listados separadamente.

## Preparação no Windows

Instale uma versão do Python compatível com o yt-dlp atual (3.11 ou superior) com Tkinter e FFmpeg. Adicione `ffmpeg` e `ffprobe` ao PATH. Abra o PowerShell nesta pasta e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Para atualizar o mecanismo quando um site mudar:

```powershell
.\.venv\Scripts\python -m pip install --upgrade "yt-dlp[default]"
```

O instalador inclui QuickJS-NG como runtime JavaScript; a compatibilidade depende das versões do yt-dlp e do site. Veja os [requisitos atuais do yt-dlp](https://github.com/yt-dlp/yt-dlp#dependencies). A análise e o download acessam os servidores da plataforma diretamente. Esta versão não oferece login nem importação de cookies. O cancelamento pode deixar arquivos parciais na pasta escolhida.

## Build de teste

Com as dependências de desenvolvimento instaladas e Inno Setup disponível, execute `python build_release.py --iscc CAMINHO_PARA_ISCC`. O script limpa somente as pastas dedicadas `build/release-build` e `dist/release-build`, gera o instalador e seu SHA-256. Para assinar, configure `ORVETA_CERT_FILE` e `ORVETA_CERT_PASSWORD`; opcionalmente informe `ORVETA_SIGNTOOL` e `ORVETA_TIMESTAMP_URL`. Sem certificado, o build é gerado sem assinatura e informa isso. O fluxo assinado ainda precisa ser validado com certificado real.

O instalador é uma versão inicial para uso pessoal e não possui assinatura digital. Antes de publicar, será necessário testar em máquinas limpas, preparar a atualização dos componentes, revisar as obrigações de distribuição das dependências e testar cada sistema operacional. Esta versão inclui uma compilação GPL do FFmpeg (BtbN/FFmpeg-Builds); sua licença é incluída na instalação e o código-fonte correspondente e as demais obrigações devem ser disponibilizados antes da distribuição pública.
