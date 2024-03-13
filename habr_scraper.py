import argparse
import os
import pathlib
import sys
import re
import threading
import signal
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

folder_regexp = r"[:?!\"*<>+/\\|]"
img_regexp = r"data-src=\"(.*?)\""
title_regexp = r"<span>(.*?)<\/span>"
href_regexp = r"(?<=<a\shref=)['\"](.*?)['\"]"
article_regexp = r"<h2 class=\"tm-title tm-title_h2\">(.*?)<\/h2>"

article_url = "https://habr.com{0}"
articles_url = "https://habr.com/ru/feed/page{0}/"

STOP_EVENT = threading.Event()


def load_content(url):
    try:
        with urlopen(url, timeout=10) as response:
            return response.read().decode()

    except (HTTPError, URLError):
        return None


def download_images(url, out_dit):
    try:
        count = 0
        page = load_content(url)
        for image_url in re.compile(img_regexp).findall(page):
            with open(os.path.join(out_dit, f"{count}.jpeg"), "wb") as image:
                image.write(urlopen(image_url).read())
            count += 1

    except (HTTPError, URLError):
        return None


def get_parse_data():
    current_page = 1

    try:
        articles_page = load_content(articles_url.format(current_page))
        for article in re.compile(article_regexp).findall(articles_page):
            href = re.compile(href_regexp).search(article).group(1)
            title = re.compile(title_regexp).search(article).group(1)

            yield href, re.sub(re.compile(folder_regexp), "_", title)

    except (HTTPError, URLError):
        current_page += 1


def clean_threads(threads):
    clean_count = 0
    for thread in threads:
        if not thread.is_alive():
            threads.remove(thread)
            thread.join()
            clean_count += 1

    return clean_count


def run_scraper(threads_count, articles, out_dir):
    threads = []
    parse_data = get_parse_data()

    while articles > 0 and not STOP_EVENT.is_set():
        if len(threads) < threads_count and len(threads) < articles:
            href, title = next(parse_data)
            new_out_dir = os.path.join(out_dir, title)

            if not os.path.exists(new_out_dir):
                os.makedirs(new_out_dir)

            thread = threading.Thread(target=download_images, args=(article_url.format(href), new_out_dir))
            threads.append(thread)
            thread.start()

        articles -= clean_threads(threads)

    while len(threads) > 0:
        clean_threads(threads)


def handle_kb_interrupt(sig, frame):
    STOP_EVENT.set()


def main():
    script_name = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
        usage=f'{script_name} [ARTICLES_NUMBER] THREAD_NUMBER OUT_DIRECTORY',
        description='Habr parser',
    )
    parser.add_argument(
        '-n', type=int, default=25, help='Number of articles to be processed',
    )
    parser.add_argument(
        'threads', type=int, help='Number of threads to run',
    )
    parser.add_argument(
        'out_dir', type=pathlib.Path, help='Directory to download habr images',
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_kb_interrupt)
    run_scraper(args.threads, args.n, args.out_dir)


if __name__ == '__main__':
    main()
