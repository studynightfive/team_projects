import ipaddress
import socket

for host in ["api.minimax.io", "api.deepseek.com", "dashscope.aliyuncs.com"]:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addrs = sorted({str(item[4][0]) for item in infos})
        print(host, addrs)
        for raw in addrs:
            ip = ipaddress.ip_address(raw.split("%", maxsplit=1)[0])
            print(
                " ",
                raw,
                "global=",
                ip.is_global,
                "private=",
                ip.is_private,
                "loopback=",
                ip.is_loopback,
            )
    except Exception as exc:  # noqa: BLE001
        print(host, "ERR", type(exc).__name__, exc)
