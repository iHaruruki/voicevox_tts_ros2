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
[README](https://github.com/VOICEVOX/voicevox_vvm/blob/main/README.md#%E9%9F%B3%E5%A3%B0%E3%83%A2%E3%83%87%E3%83%ABvvm%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%A8%E5%A3%B0%E3%82%AD%E3%83%A3%E3%83%A9%E3%82%AF%E3%82%BF%E3%83%BC%E3%82%B9%E3%82%BF%E3%82%A4%E3%83%AB%E5%90%8D%E3%81%A8%E3%82%B9%E3%82%BF%E3%82%A4%E3%83%AB-id-%E3%81%AE%E5%AF%BE%E5%BF%9C%E8%A1%A8)