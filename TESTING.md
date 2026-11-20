# Checklist manual do Orveta

Ainda não executado. Registrar versão, data e resultados ao testar.

- [ ] Em Windows 10 e 11 limpos, instalar por usuário, abrir o aplicativo e verificar atalhos.
- [ ] Atualizar sobre uma versão anterior usando a mesma conta e confirmar a preservação de histórico e preferências.
- [ ] Desinstalar e verificar os arquivos restantes e a preservação dos downloads pessoais.
- [ ] Instalar silenciosamente com `/VERYSILENT` e verificar o código de saída e os arquivos instalados.
- [ ] Em DPI alto, verificar controles, foco, teclado e textos nas cinco abas e em todos os idiomas.
- [ ] Com o aplicativo já aberto, executar `./capture_ui.ps1 -OutputPath C:\Temp\orveta.png` para produzir uma captura para revisão; repetir em cada aba e escala. O script requer uma sessão gráfica interativa do Windows.
- [ ] Medir início com `python measure_startup.py CAMINHO_DO_EXE` em uma sessão Windows; o número indica criação da janela, não tempo até conclusão de operações de rede.
- [ ] Testar YouTube com runtime JavaScript e sem runtime, observando o aviso e o resultado.
- [ ] Validar que diagnóstico e logs não contêm URLs, nomes de arquivos, cookies ou dados da conta após operações normais e com falhas.
- [ ] Em um pacote de teste, conferir que `yt-dlp.exe`, `runtime/qjs.exe`, os executáveis e DLLs do FFmpeg, os arquivos em `_internal/` e os avisos em `licenses/` estão presentes.
- [ ] Testar análise, download, conversão, fila, cancelamento, legendas, playlists e histórico com conteúdo autorizado.
- [ ] Testar a atualização do yt-dlp nos canais stable e nightly, incluindo falha de rede, checksum incorreto e tentativa de recuperação após erro de extração.
- [ ] Com o app fechado, validar o SHA-256 publicado ao lado do instalador e testar `build_release.py --iscc <caminho>` em ambiente preparado.
- [ ] Em ambiente de teste com certificado, configurar `ORVETA_CERT_FILE`, `ORVETA_CERT_PASSWORD` e, se necessário, `ORVETA_SIGNTOOL` e `ORVETA_TIMESTAMP_URL`; validar as assinaturas do aplicativo, instalador e desinstalador. Não registrar a senha em relatórios.
- [ ] Verificar assinatura digital e desinstalador quando houver certificado.
- [ ] Conferir licenças, avisos e disponibilização dos fontes exatos com assessoria jurídica antes da distribuição pública.
