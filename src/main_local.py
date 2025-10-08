"""
Local model version of the main fact-checking system.
This replaces OpenAI API calls with local model calls while keeping all other functionality.
"""

import sys
import argparse
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import SETTINGS to force-load and validate env on startup
from .utils.config import SETTINGS  # noqa: F401
from .utils.local_claims import (
    extract_claims_from_query,
    optimize_claim,
    get_query_for_wiki_article,
)
from .utils.google_custom_search import get_first_n_results_urls
from .utils.wikipedia_scraper import scrape_wikipedia_content
from .utils.local_factcheck_full import find_answer_in_article, build_text_fragment_link
from .utils.local_openai_client import LocalOpenAIClient, set_local_openai_client


def process_single_claim(claim: str, top_n_urls: int = 1) -> dict:
    """Process a single claim and return results with timing info."""
    start_time = time.time()

    print(f"\n\nEvaluating claim: {claim}")

    # Optimize claim
    opt_start = time.time()
    optimized = optimize_claim(claim)
    opt_time = time.time() - opt_start
    print(f"Optimized claim: {optimized} (took {opt_time:.2f}s)")

    # Get Wikipedia article query
    query_start = time.time()
    article_query = get_query_for_wiki_article(claim)
    query_time = time.time() - query_start
    print(f"Wikipedia Article To Check: {article_query} (took {query_time:.2f}s)")

    # Get URLs
    url_start = time.time()
    urls = get_first_n_results_urls(article_query, top_n_urls)
    url_time = time.time() - url_start
    print(f"URLs Fetched: {urls} (took {url_time:.2f}s)")

    if not urls:
        print("No URL found from search")
        return {
            "claim": claim,
            "optimized": optimized,
            "article_query": article_query,
            "urls": None,
            "result": None,
            "total_time": time.time() - start_time,
            "timing": {
                "optimize": opt_time,
                "query": query_time,
                "urls": url_time,
                "scrape": 0,
                "factcheck": 0,
            },
        }

    # Scrape content from all URLs in parallel
    print(f"\nScraping content from {len(urls)} Wikipedia article(s)...")
    scrape_start = time.time()

    def scrape_url(url):
        return scrape_wikipedia_content(url)

    contents = []
    with ThreadPoolExecutor(max_workers=min(len(urls), 3)) as executor:
        future_to_url = {executor.submit(scrape_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                if content:
                    contents.append((url, content))
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")

    scrape_time = time.time() - scrape_start
    print(f"Scraping completed in {scrape_time:.2f}s")

    if not contents:
        print("Failed to scrape content from any URL")
        return {
            "claim": claim,
            "optimized": optimized,
            "article_query": article_query,
            "urls": urls,
            "result": None,
            "total_time": time.time() - start_time,
            "timing": {
                "optimize": opt_time,
                "query": query_time,
                "urls": url_time,
                "scrape": scrape_time,
                "factcheck": 0,
            },
        }

    # Use the first successfully scraped content for fact-checking
    url, content = contents[0]

    # Fact-check
    factcheck_start = time.time()
    result = find_answer_in_article(content, claim)
    factcheck_time = time.time() - factcheck_start

    if result:
        print("\n=== Answer from article ===")
        print(f"Label: {result.label}")
        print(f"Evidence: {result.evidence}")
    else:
        print("Failed to get response")

    print("\n=== LINK TO RESPONSE ===")
    link = build_text_fragment_link(url, result.evidence if result else None)
    print(link)

    total_time = time.time() - start_time
    print(f"Total time for claim: {total_time:.2f}s")

    return {
        "claim": claim,
        "optimized": optimized,
        "article_query": article_query,
        "urls": urls,
        "result": result,
        "total_time": total_time,
        "timing": {
            "optimize": opt_time,
            "query": query_time,
            "urls": url_time,
            "scrape": scrape_time,
            "factcheck": factcheck_time,
        },
    }


def process_query_sequential(query: str, top_n_urls: int = 1) -> int:
    """Original sequential processing for comparison."""
    start_time = time.time()
    print(f"Query: {query}")

    # Extract claims
    claims_start = time.time()
    claims = extract_claims_from_query(query)
    claims_time = time.time() - claims_start
    print(f"Claims: {claims} (extraction took {claims_time:.2f}s)")

    if not claims:
        print("No claims found to process")
        return 0

    # Process claims sequentially
    print(f"\nProcessing {len(claims)} claims sequentially...")
    results = []

    for claim in claims:
        result = process_single_claim(claim, top_n_urls)
        results.append(result)

    # Print summary
    total_time = time.time() - start_time
    print(f"\n{'=' * 50}")
    print("SEQUENTIAL SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Claims extraction time: {claims_time:.2f}s")
    print(f"Claims processing time: {total_time - claims_time:.2f}s")

    if results:
        avg_claim_time = sum(r["total_time"] for r in results) / len(results)
        print(f"Average time per claim: {avg_claim_time:.2f}s")

    return 0


def process_query_parallel(query: str, top_n_urls: int = 1) -> int:
    """Parallel processing version."""
    start_time = time.time()
    print(f"Query: {query}")

    # Extract claims
    claims_start = time.time()
    claims = extract_claims_from_query(query)
    claims_time = time.time() - claims_start
    print(f"Claims: {claims} (extraction took {claims_time:.2f}s)")

    if not claims:
        print("No claims found to process")
        return 0

    # Process claims in parallel
    print(f"\nProcessing {len(claims)} claims in parallel...")
    results = []

    with ThreadPoolExecutor(max_workers=min(len(claims), 3)) as executor:
        future_to_claim = {
            executor.submit(process_single_claim, claim, top_n_urls): claim
            for claim in claims
        }

        for future in as_completed(future_to_claim):
            claim = future_to_claim[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Failed to process claim '{claim}': {e}")

    # Print summary
    total_time = time.time() - start_time
    print(f"\n{'=' * 50}")
    print("PARALLEL SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Claims extraction time: {claims_time:.2f}s")
    print(f"Claims processing time: {total_time - claims_time:.2f}s")

    if results:
        avg_claim_time = sum(r["total_time"] for r in results) / len(results)
        print(f"Average time per claim: {avg_claim_time:.2f}s")

        # Timing breakdown
        total_optimize = sum(r["timing"]["optimize"] for r in results)
        total_query = sum(r["timing"]["query"] for r in results)
        total_urls = sum(r["timing"]["urls"] for r in results)
        total_scrape = sum(r["timing"]["scrape"] for r in results)
        total_factcheck = sum(r["timing"]["factcheck"] for r in results)

        print("\nTiming breakdown:")
        print(f"  - Claim optimization: {total_optimize:.2f}s")
        print(f"  - Wiki query generation: {total_query:.2f}s")
        print(f"  - URL fetching: {total_urls:.2f}s")
        print(f"  - Content scraping: {total_scrape:.2f}s")
        print(f"  - Fact-checking: {total_factcheck:.2f}s")

    return 0


def process_query(query: str, top_n_urls: int = 1, parallel: bool = True) -> int:
    """Process query with optional parallelization."""
    if parallel:
        return process_query_parallel(query, top_n_urls)
    else:
        return process_query_sequential(query, top_n_urls)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Fact-check claims against Wikipedia using local models.")
    parser.add_argument("query", nargs="+", help="The query text to analyze")
    parser.add_argument(
        "--top-n", type=int, default=1, help="Number of top URLs to fetch"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Use sequential processing instead of parallel (for comparison)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run both sequential and parallel versions for comparison",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234",
        help="Base URL for local model server"
    )
    parser.add_argument(
        "--model",
        default="local-model",
        help="Model name to use"
    )
    args = parser.parse_args(argv)

    # Set up local model client
    local_client = LocalOpenAIClient(args.base_url, args.model)
    set_local_openai_client(local_client)
    
    print(f"Using local model at {args.base_url} with model '{args.model}'")

    query = " ".join(args.query)

    if args.compare:
        print("Running comparison between sequential and parallel processing...\n")

        # Run sequential first
        print("=" * 60)
        print("SEQUENTIAL PROCESSING")
        print("=" * 60)
        process_query(query, args.top_n, parallel=False)

        print("\n" + "=" * 60)
        print("PARALLEL PROCESSING")
        print("=" * 60)
        process_query(query, args.top_n, parallel=True)

        return 0
    else:
        return process_query(query, args.top_n, parallel=not args.sequential)


if __name__ == "__main__":
    sys.exit(main())
