import sys
import argparse
from typing import Optional

# Import SETTINGS to force-load and validate env on startup
from .utils.config import SETTINGS  # noqa: F401
from .utils.claims import (
    extract_claims_from_query,
    optimize_claim,
    get_query_for_wiki_article,
)
from .utils.google_custom_search import get_first_n_results_urls
from .utils.wikipedia_scraper import scrape_wikipedia_content
from .utils.factcheck import find_answer_in_article, build_text_fragment_link


def process_query(query: str, top_n_urls: int = 1) -> int:
    print(f"Query: {query}")
    claims = extract_claims_from_query(query)
    print("Claims:", claims)

    for claim in claims:
        print("\n\nEvaluating claim:", claim)

        optimized = optimize_claim(claim)
        print("Optimized claim:", optimized)

        article_query = get_query_for_wiki_article(claim)
        print("Wikipedia Article To Check:", article_query)

        urls = get_first_n_results_urls(article_query, top_n_urls)
        print("URLs Fetched:", urls)

        if not urls:
            print("No URL found from search")
            continue

        print("\nScraping content from Wikipedia article...")
        content = scrape_wikipedia_content(urls[0])

        if not content:
            print("Failed to scrape content from the URL")
            continue

        result = find_answer_in_article(content, claim)
        if result:
            print("\n=== Answer from article ===")
            print("Label:", result.label)
            print("Evidence:", result.evidence)
        else:
            print("Failed to get response")

        print("\n=== LINK TO RESPONSE ===")
        link = build_text_fragment_link(urls[0], result.evidence if result else None)
        print(link)

    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Fact-check claims against Wikipedia.")
    parser.add_argument("query", nargs="+", help="The query text to analyze")
    parser.add_argument(
        "--top-n", type=int, default=1, help="Number of top URLs to fetch"
    )
    args = parser.parse_args(argv)

    query = " ".join(args.query)
    return process_query(query, args.top_n)


if __name__ == "__main__":
    sys.exit(main())
