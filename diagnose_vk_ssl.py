import socket
import ssl

import requests


def check_host(host: str) -> None:
    print(f"\n=== {host} ===")

    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as secure_sock:
                cert = secure_sock.getpeercert()
                print("issuer:", cert.get("issuer"))
                print("subject:", cert.get("subject"))
    except Exception as exc:
        print("ssl_error:", repr(exc))

    try:
        response = requests.get(
            f"https://{host}/method/users.get?v=5.199",
            timeout=10,
        )
        print("http_status:", response.status_code)
        print("body:", response.text[:300])
    except Exception as exc:
        print("requests_error:", repr(exc))


def main() -> None:
    for host in ("api.vk.ru", "api.vk.com"):
        check_host(host)


if __name__ == "__main__":
    main()
