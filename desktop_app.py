import threading
import webbrowser
from app import create_server


def main():
    httpd = create_server(0)
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    try:
        import webview

        webview.create_window(
            "Product Image Helper",
            url,
            width=1240,
            height=840,
            min_size=(960, 680),
        )
        webview.start()
    except ImportError:
        print(f"pywebview not installed; opening browser at {url}")
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
