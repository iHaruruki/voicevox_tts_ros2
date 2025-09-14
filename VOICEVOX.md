# Setup VOICEBOX
### Install libralies
```shell
$ sudo apt update
$ sudo apt install p7zip
$ sudo apt install curl
$ sudo apt install libfuse2
$ sudo add-apt-repository universe
```
### Install VOICEVOX
1. Open the link - [voicevox](https://voicevox.hiroshiba.jp/)
2. Click `ダウンロード` button
3. Download OS:`Linux`, 対応モード:`CPU(x64)`, パッケージ: `インストーラー`
4. Give execution permission
```shell
chmod +x VOICEVOX-CPU-X64.Installer.0.24.2.Linux.sh
```
5. Install
```shell
./VOICEVOX-CPU.Installer.0.15.2.Linux.sh
```
6. Open the VOICEVOX
```shell
./.voicevox/VOICEVOX.AppImage
```
### 音声モデルファイルと声とスタイルIDの対応表
[README](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md)