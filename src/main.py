import sys
import argparse
import time
from typing import Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import SETTINGS to force-load and validate env on startup
from .utils.config import SETTINGS  # noqa: F401
from .utils.claims import (
    get_query_for_wiki_article,
    generate_plan,
    extract_answer_from_article,
    generate_final_claim,
    extract_claims_from_query,
)
from .utils.google_custom_search import get_first_n_results_urls
from .utils.wikipedia_scraper import scrape_wikipedia_content, extract_title_from_wiki_url
from .utils.factcheck import find_answer_in_article, build_text_fragment_link


# Global cache for scraped articles: maps article title to (url, content) tuple
Scraped_Articles_Cache: Dict[str, Tuple[str, str]] = {}


def get_or_scrape_article(article_query: str, top_n_urls: int = 1) -> Tuple[Optional[str], Optional[str]]:
    """
    Get article content from cache or scrape it.
    Returns (url, content) tuple or (None, None) if not found.
    """
    # Not in cache, need to scrape
    print(f"Article '{article_query}' not in cache, fetching...")
    urls = get_first_n_results_urls(article_query, top_n_urls)
    
    if not urls:
        print(f"No URL found for article query: {article_query}")
        return None, None
    
    # Scrape the first URL
    url = urls[0]
    
    # Extract title from URL to use as cache key
    article_title = extract_title_from_wiki_url(url)
    if not article_title:
        # Fallback: use article_query as key
        article_title = article_query
    
    # Check cache using extracted title
    if article_title in Scraped_Articles_Cache:
        print(f"Article '{article_title}' found in cache")
        cached_url, cached_content = Scraped_Articles_Cache[article_title]
        return cached_url, cached_content
    
    # Not in cache, scrape it
    content = scrape_wikipedia_content(url)
    
    if content:
        # Store in cache using article title as key
        Scraped_Articles_Cache[article_title] = (url, content)
        print(f"Article '{article_title}' scraped and cached")
        return url, content
    
    return None, None


def process_query_new_flow(query: str, top_n_urls: int = 1) -> int:
    """
    New multi-step fact-checking flow with plan-based approach:
    1. Generate plan (prerequisites, additional info needed, final claim template)
    2. Loop through prerequisites and validate each
    3. Loop through additional info needed and extract each
    4. Generate final claim from template and extracted info
    5. Check final claim
    """
    global Scraped_Articles_Cache
    
    start_time = time.time()
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print(f"{'=' * 60}\n")
    
    # Initialize cache
    Scraped_Articles_Cache = {}
    print("Scraped Articles Cache: []\n")
    
    # Step 1: Generate plan
    print("Generating fact-checking plan...")
    plan_start = time.time()
    plan = generate_plan(query)
    plan_time = time.time() - plan_start
    
    if not plan.prerequisites and not plan.additional_info_needed:
        print("Failed to generate plan or plan is empty")
        return 1
    
    print(f"Plan generated (took {plan_time:.2f}s):")
    print(f"  Prerequisites ({len(plan.prerequisites)}): {plan.prerequisites}")
    print(f"  Additional info needed ({len(plan.additional_info_needed)}): {[item.purpose for item in plan.additional_info_needed]}")
    print(f"  Final claim template: {plan.final_claim_template}\n")
    
    # Step 2: Validate prerequisites (loop)
    print("Validating pre-requisite info:")
    for i, prerequisite in enumerate(plan.prerequisites, 1):
        print(f"\nPrerequisite {i}/{len(plan.prerequisites)}: \"{prerequisite}\"")
        
        # Get article for prerequisite
        print(f"-> LLM selects wikipedia article...")
        article_start = time.time()
        article_query = get_query_for_wiki_article(prerequisite)
        article_time = time.time() - article_start
        
        if not article_query:
            print(f"Failed to get article query for prerequisite")
            return 1
        
        print(f"Article selected: \"{article_query}\" (took {article_time:.2f}s)")
        
        # Get or scrape article
        url, content = get_or_scrape_article(article_query, top_n_urls)
        
        if not content:
            print(f"Failed to scrape article for prerequisite")
            return 1
        
        print(f"Article and scraped text key value pair stored into Scraped_Articles_Cache")
        print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}")
        
        # Fact check prerequisite
        print("-> Fact check is ran on prerequisite...")
        factcheck_start = time.time()
        result = find_answer_in_article(content, prerequisite)
        factcheck_time = time.time() - factcheck_start
        
        if not result:
            print(f"Failed to fact-check prerequisite")
            return 1
        
        print(f"Prerequisite result: {result.label}")
        print(f"Evidence: {result.evidence[:100]}..." if len(result.evidence) > 100 else f"Evidence: {result.evidence}")
        
        if result.label != "True":
            print(f"Prerequisite validation failed, cannot proceed")
            return 1
        
        print(f"Prerequisite {i} validated ✓")
    
    if plan.prerequisites:
        print("\nAll prerequisites validated, proceed\n")
    
    # Step 3: Extract additional info (loop)
    extracted_info = {}
    
    if plan.additional_info_needed:
        print("Additional info required to validate? Yes:")
        for i, info_item in enumerate(plan.additional_info_needed, 1):
            question = info_item.question
            purpose = info_item.purpose
            
            print(f"\nExtracting info {i}/{len(plan.additional_info_needed)}: {purpose}")
            print(f"Question: \"{question}\"")
            
            # Enhance question with previously extracted information
            enhanced_question = question
            if extracted_info:
                # Create context string from extracted info in a clear format
                context_lines = [f"- {key}: {value}" for key, value in extracted_info.items()]
                context_str = "Previously extracted information:\n" + "\n".join(context_lines)
                enhanced_question = f"{question}\n\n{context_str}"
                print(f"Enhanced question with context: {extracted_info}")
            
            # Get article for question (use enhanced question for better article selection)
            print(f"-> LLM selects wikipedia article...")
            article_start = time.time()
            article_query = get_query_for_wiki_article(enhanced_question)
            article_time = time.time() - article_start
            
            if not article_query:
                print(f"Failed to get article query")
                return 1
            
            print(f"Article selected: \"{article_query}\" (took {article_time:.2f}s)")
            
            # Get or scrape article (will use cache if same article)
            cache_size_before = len(Scraped_Articles_Cache)
            info_url, info_content = get_or_scrape_article(article_query, top_n_urls)
            
            if not info_content:
                print(f"Failed to scrape article")
                return 1
            
            cache_size_after = len(Scraped_Articles_Cache)
            if cache_size_after > cache_size_before:
                print(f"Article scraped and cached")
                print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}")
            else:
                print(f"Article already in cache, using cached content")
            
            # Extract answer from article (use enhanced question with context)
            print(f"-> Running question on article...")
            extract_start = time.time()
            answer = extract_answer_from_article(enhanced_question, info_content)
            extract_time = time.time() - extract_start
            
            if not answer or answer == "NOT_FOUND":
                print(f"Failed to extract answer")
                return 1
            
            print(f"LLM Returns \"{answer}\" (took {extract_time:.2f}s)")
            
            # Store extracted info
            extracted_info[purpose] = answer
    
    # Step 4: Generate final claim
    print("\nFinal Claim to Check:")
    final_claim_start = time.time()
    final_claim = generate_final_claim(query, plan.final_claim_template, extracted_info)
    final_claim_time = time.time() - final_claim_start
    
    if not final_claim:
        print("Failed to generate final claim")
        return 1
    
    print(f"-> Use template and extracted info to generate a concise claim")
    print(f"LLM generates: \"{final_claim}\" (took {final_claim_time:.2f}s)\n")
    
    # Step 5: Final check
    print("Final Check Step:")
    final_article_start = time.time()
    final_article_query = get_query_for_wiki_article(final_claim)
    final_article_time = time.time() - final_article_start
    
    if not final_article_query:
        print("Failed to get article query for final claim")
        return 1
    
    print(f"-> Run fact check on claim, (article fetched will be {final_article_query})")
    
    cache_size_before = len(Scraped_Articles_Cache)
    final_url, final_content = get_or_scrape_article(final_article_query, top_n_urls)
    
    if not final_content:
        print("Failed to scrape article for final claim")
        return 1
    
    cache_size_after = len(Scraped_Articles_Cache)
    if cache_size_after > cache_size_before:
        print(f"Article scraped and stored into cache")
        print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}\n")
    else:
        print(f"Article already in cache")
    
    # Fact check final claim
    print("\n-> Running final fact check...")
    final_factcheck_start = time.time()
    final_result = find_answer_in_article(final_content, final_claim)
    final_factcheck_time = time.time() - final_factcheck_start
    
    if final_result:
        print("\n=== Final Answer ===")
        print(f"Label: {final_result.label}")
        print(f"Evidence: {final_result.evidence}")
        print("\n=== LINK TO RESPONSE ===")
        link = build_text_fragment_link(final_url, final_result.evidence if final_result else None)
        print(link)
    else:
        print("Failed to get response for final claim")
    
    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Total time: {total_time:.2f}s")
    print(f"{'=' * 60}\n")
    
    return 0


def process_query_new_flow_with_claims_split(query: str, top_n_urls: int = 1, parallel: bool = False) -> int:
    """
    Split query into multiple claims, then run the new flow on each claim.
    Combines claim extraction with the new multi-step fact-checking flow.
    """
    start_time = time.time()
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print(f"{'=' * 60}\n")
    
    # Step 1: Extract claims from query
    print("Extracting claims from query...")
    claims_start = time.time()
    claims = extract_claims_from_query(query)
    claims_time = time.time() - claims_start
    
    if not claims:
        print("No claims found to process")
        return 0
    
    print(f"Extracted {len(claims)} claim(s) (took {claims_time:.2f}s):")
    for i, claim in enumerate(claims, 1):
        print(f"  {i}. {claim}")
    print()
    
    # Step 2: Process each claim with the new flow
    if parallel:
        print(f"Processing {len(claims)} claims in parallel with new flow...\n")
        results = []
        
        with ThreadPoolExecutor(max_workers=min(len(claims), 3)) as executor:
            future_to_claim = {
                executor.submit(process_query_new_flow, claim, top_n_urls): claim
                for claim in claims
            }
            
            for future in as_completed(future_to_claim):
                claim = future_to_claim[future]
                try:
                    result = future.result()
                    results.append((claim, result))
                except Exception as e:
                    print(f"Failed to process claim '{claim}': {e}")
                    results.append((claim, 1))
    else:
        print(f"Processing {len(claims)} claims sequentially with new flow...\n")
        results = []
        for i, claim in enumerate(claims, 1):
            print(f"\n{'#' * 60}")
            print(f"Processing Claim {i}/{len(claims)}")
            print(f"{'#' * 60}")
            try:
                result = process_query_new_flow(claim, top_n_urls)
                results.append((claim, result))
            except Exception as e:
                print(f"Failed to process claim '{claim}': {e}")
                results.append((claim, 1))
    
    # Print summary
    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Claims extraction time: {claims_time:.2f}s")
    print(f"Claims processing time: {total_time - claims_time:.2f}s")
    
    successful = sum(1 for _, result in results if result == 0)
    failed = len(results) - successful
    print(f"Successful: {successful}/{len(results)}, Failed: {failed}/{len(results)}")
    
    return 0 if successful == len(results) else 1


def process_single_claim(claim: str, top_n_urls: int = 1) -> dict:
    """Legacy single claim processing (kept for backward compatibility)."""
    start_time = time.time()

    print(f"\n\nEvaluating claim: {claim}")

    # Optimize claim
    opt_start = time.time()
    from .utils.claims import optimize_claim
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
    from .utils.claims import extract_claims_from_query
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


def process_query(query: str, top_n_urls: int = 1, parallel: bool = True) -> int:
    """Process query with optional parallelization."""
    if parallel:
        return process_query_parallel(query, top_n_urls)
    else:
        return process_query_sequential(query, top_n_urls)


def process_query_parallel(query: str, top_n_urls: int = 1) -> int:
    """Parallel processing version."""
    start_time = time.time()
    print(f"Query: {query}")

    # Extract claims
    claims_start = time.time()
    from .utils.claims import extract_claims_from_query
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


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Fact-check claims against Wikipedia.")
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
        "--new-flow",
        action="store_true",
        help="Use the new multi-step fact-checking flow",
    )
    parser.add_argument(
        "--new-flow-split",
        action="store_true",
        help="Split query into claims, then run new flow on each claim",
    )
    args = parser.parse_args(argv)

    query = " ".join(args.query)

    if args.new_flow_split:
        return process_query_new_flow_with_claims_split(query, args.top_n, parallel=not args.sequential)
    
    if args.new_flow:
        return process_query_new_flow(query, args.top_n)

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
