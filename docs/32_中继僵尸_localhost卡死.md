# 32 Windows 侧 localhost 中继僵尸态：端口仍监听但 localhost 连接卡死（2026-08-21）

> 状态：已完成取证。开发环境 Windows 浏览器访问 localhost:8080 持续转圈；定位为 WSL localhost 转发中继（dllhost.exe 进程）僵尸态，与 #41286 端口注册链失效属不同故障层。

## 一、事件背景

- 2026-08-20 与 08-21 多次 WSL / Docker Desktop 重启后，Dashboard 前端（Windows 浏览器访问 `http://localhost:8080`）持续转圈无法打开。
- WSL 内服务本身正常：kubectl port-forward 监听 0.0.0.0:8080，WSL 内 curl 127.0.0.1:8080 与局域网 IP 均可访问。
- 仅 Windows 侧 localhost（127.0.0.1 / ::1）访问 hang；换局域网 IP（`http://192.168.10.227:8080`）立即正常。

## 二、现场证据（2026-08-21）

netstat -ano 过滤 :8080 的关键行：

```text
TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       58264
TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING       58264
TCP    192.168.10.227:8080    192.168.10.227:54703   ESTABLISHED     58264
TCP    [::1]:8080             [::1]:50351            CLOSE_WAIT      58264
TCP    [::1]:50351            [::1]:8080             FIN_WAIT_2      17188
```

- 进程：PID 58264 = dllhost.exe（C:\Windows\system32\DllHost.exe，启动于 2026-08-20 12:05:10，COM 代理宿主）。
- WSL 侧：kubectl port-forward 监听 0.0.0.0:8080（服务存活）。
- netsh interface portproxy show all 为空：不是 netsh 端口代理，中继由 WSL 组件承载。

## 三、判断

- WSL 的 localhost 转发中继（Windows 侧 COM 代理进程 dllhost.exe 承载）进入僵尸态：端口仍监听、LAN IP 路径仍转发，但 localhost 路径新连接 hang，半关闭连接（CLOSE_WAIT / FIN_WAIT_2）堆积。
- 与 #41286 / #41383（WSL 内新端口注册链失效）不同层：前者是 Windows 侧中继进程问题，后者是 WSL 内注册链问题；两者同属 localhost 转发链，可叠加出现。

## 四、规避与根治

- 规避（零成本）：开发环境服务监听 0.0.0.0，浏览器用局域网 IP 访问；恢复步骤见 08_系统恢复操作步骤.md。
- 根治：wsl --shutdown 重置中继（影响运行中发行版与 Docker Desktop 内置 K8s，需确认后执行）；或整机重启。
- 验证是否恢复：Windows 侧 netstat 确认 8080 不再由 dllhost 持有，且 localhost:8080 新连接立即返回。

## 五、关联

- 与 28_kind_pv_tmpfs恢复SOP.md 同属「重启后环境恢复」主题。
- 为 localhost 转发链故障增加一个可辨识形态：监听在 + LAN IP 通 + localhost hang + CLOSE_WAIT 堆积，先查 Windows 侧中继进程，而不是在 WSL 内反复重启服务。
