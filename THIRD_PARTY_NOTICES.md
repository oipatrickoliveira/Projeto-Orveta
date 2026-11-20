# Avisos de componentes de terceiros

Esta lista é preliminar e precisa de revisão antes de distribuição pública. O Orveta executa os componentes abaixo como programas separados, além dos componentes empacotados pelo PyInstaller.

- **yt-dlp 2026.10.26**: o projeto principal usa a Unlicense; o executável oficial inclui componentes de terceiros, incluindo componentes GPLv3+. Os avisos da versão distribuída acompanham a instalação em `yt-dlp-THIRD_PARTY_LICENSES.txt`. Fontes e release: https://github.com/yt-dlp/yt-dlp/tree/2026.10.26 e https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.26. Atualizações posteriores podem ter versões e avisos diferentes.
- **FFmpeg e ffprobe**: compilação compartilhada GPLv3+ identificada pelo próprio executável como `n8.1.3-36-ge22a4510c9-20261119`. A licença incluída é `FFmpeg-LICENSE.txt`; a árvore do FFmpeg correspondente ao identificador está em https://github.com/FFmpeg/FFmpeg/tree/e22a4510c9, e o projeto de compilação em https://github.com/FFmpeg-Builds/FFmpeg-Builds. A identificação exata dos scripts de compilação, das bibliotecas incluídas e a forma de disponibilização do código correspondente ainda precisam ser confirmadas; não tratar este aviso como prova de conformidade.
- **QuickJS-NG 0.18.0**: licença MIT em `QuickJS-NG-LICENSE.txt`. Fonte: https://github.com/quickjs-ng/quickjs/tree/v0.18.0. O aplicativo usa `qjs.exe` como runtime JavaScript opcional do yt-dlp.
- **Python**: a licença da instalação usada na compilação acompanha o aplicativo como `Python-LICENSE.txt`. Fonte: https://www.python.org/downloads/source/.
- **Tcl/Tk**: a licença dos componentes da instalação Python utilizada acompanha o aplicativo como `Tcl-Tk-LICENSE.txt`. Fontes: https://github.com/tcltk/tcl e https://github.com/tcltk/tk.

As obrigações de licenciamento dos binários, bibliotecas transitivas, atualizações e ferramentas de empacotamento devem ser verificadas para cada release. O instalador ainda não é considerado pronto para publicação comercial.
