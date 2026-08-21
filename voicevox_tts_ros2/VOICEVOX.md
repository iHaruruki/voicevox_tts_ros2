# VOICEVOX

## Setup
### Install libralies
```bash
sudo apt update
sudo apt install -y p7zip curl libfuse2
sudo add-apt-repository universe
```
### Install VOICEVOX
1. Open the link - [voicevox](https://voicevox.hiroshiba.jp/)
2. Click `ダウンロード` button
3. Download OS:`Linux`, 対応モード:`CPU(x64)`, パッケージ: `インストーラー`
4. Give execution permission
```bash
chmod +x VOICEVOX-CPU-X64.Installer.0.24.2.Linux.sh
```
5. Install
```bash
./VOICEVOX-CPU.Installer.0.15.2.Linux.sh
```
6. Open the VOICEVOX
```bash
./.voicevox/VOICEVOX.AppImage
```
## References
* [voicevox_core](https://github.com/VOICEVOX/voicevox_core.git)
* [voicevox_engine](https://github.com/VOICEVOX/voicevox_engine.git)
* [voicevox_vvm](https://github.com/VOICEVOX/voicevox_vvm.git)
* [](https://zunko.jp/)

> [!NOTE]
> This software uses the VOICEVOX Engine (MIT License).<br>
> VOICEVOX: https://voicevox.hiroshiba.jp/<br>
> Generated voices (e.g., 四国めたん, ずんだもん) are subject to each character's usage guidelines.