"""
FastAPI server for The Truth Machine frontend.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Generator
import time
import asyncio
import json
from contextlib import asynccontextmanager

from src.utils.config import SETTINGS  # noqa: F401
from src.utils.claims import (
    get_query_for_wiki_article,
    generate_plan,
    extract_answer_from_article,
    generate_final_claim,
    extract_claims_from_query,
)
from src.utils.google_custom_search import get_first_n_results_urls
from src.utils.wikipedia_scraper import scrape_wikipedia_content, extract_title_from_wiki_url
from src.utils.factcheck import find_answer_in_article, build_text_fragment_link


# Global cache for scraped articles
Scraped_Articles_Cache: Dict[str, tuple[str, str]] = {}


class QueryRequest(BaseModel):
    query: str
    top_n_urls: int = 1


class ValidationStatus(BaseModel):
    status: str  # "pending", "validating", "validated", "failed"
    label: Optional[str] = None
    evidence: Optional[str] = None
    article_query: Optional[str] = None
    article_url: Optional[str] = None
    link: Optional[str] = None
    error: Optional[str] = None


class PrerequisiteNode(BaseModel):
    text: str
    validation: ValidationStatus


class AdditionalInfoNode(BaseModel):
    purpose: str
    question: str
    answer: Optional[str] = None
    validation: ValidationStatus


class ClaimNode(BaseModel):
    text: str
    prerequisites: List[PrerequisiteNode]
    additional_info: List[AdditionalInfoNode]
    final_claim: Optional[str] = None
    final_validation: Optional[ValidationStatus] = None


class FactCheckResponse(BaseModel):
    query: str
    claims: List[ClaimNode]
    total_time: Optional[float] = None


class ProgressUpdate(BaseModel):
    type: str  # "step", "claim", "prerequisite", "additional_info", "final_claim", "complete", "error"
    message: str
    data: Optional[Dict] = None


def get_or_scrape_article(article_query: str, top_n_urls: int = 1) -> tuple[Optional[str], Optional[str]]:
    """Get article content from cache or scrape it."""
    urls = get_first_n_results_urls(article_query, top_n_urls)
    
    if not urls:
        return None, None
    
    url = urls[0]
    article_title = extract_title_from_wiki_url(url)
    if not article_title:
        article_title = article_query
    
    if article_title in Scraped_Articles_Cache:
        cached_url, cached_content = Scraped_Articles_Cache[article_title]
        return cached_url, cached_content
    
    content = scrape_wikipedia_content(url)
    
    if content:
        Scraped_Articles_Cache[article_title] = (url, content)
        return url, content
    
    return None, None


def process_claim_with_plan(claim: str, top_n_urls: int = 1) -> ClaimNode:
    """Process a single claim with the new flow and return structured data (non-streaming version)."""
    return process_claim_with_plan_streaming(claim, top_n_urls, progress_callback=None)


def process_claim_with_plan_streaming(
    claim: str, 
    top_n_urls: int = 1,
    progress_callback: Optional[callable] = None
) -> ClaimNode:
    """Process a single claim with the new flow and return structured data."""
    global Scraped_Articles_Cache
    
    print(f"\n{'=' * 60}")
    print(f"Processing claim: {claim}")
    print(f"{'=' * 60}\n")
    
    # Initialize cache for this claim
    Scraped_Articles_Cache = {}
    print("Scraped Articles Cache: []\n")
    
    # Step 1: Generate plan
    print("Generating fact-checking plan...")
    if progress_callback:
        progress_callback("step", f"Generating fact-checking plan for: {claim}")
    plan_start = time.time()
    plan = generate_plan(claim)
    plan_time = time.time() - plan_start
    
    if not plan.prerequisites and not plan.additional_info_needed:
        print("Failed to generate plan or plan is empty")
        if progress_callback:
            progress_callback("error", "Failed to generate plan or plan is empty")
        return ClaimNode(
            text=claim,
            prerequisites=[],
            additional_info=[],
            final_claim=None,
            final_validation=ValidationStatus(
                status="failed",
                error="Failed to generate plan or plan is empty"
            )
        )
    
    print(f"Plan generated (took {plan_time:.2f}s):")
    print(f"  Prerequisites ({len(plan.prerequisites)}): {plan.prerequisites}")
    print(f"  Additional info needed ({len(plan.additional_info_needed)}): {[item.purpose for item in plan.additional_info_needed]}")
    print(f"  Final claim template: {plan.final_claim_template}\n")
    
    if progress_callback:
        progress_callback("step", f"Plan generated: {len(plan.prerequisites)} prerequisites, {len(plan.additional_info_needed)} additional info items")
        # Immediately send plan structure so UI can show all items with loading states
        progress_callback("plan_generated", "Plan structure ready", {
            "prerequisites": plan.prerequisites,
            "additional_info": [{"purpose": item.purpose, "question": item.question} for item in plan.additional_info_needed],
            "final_claim_template": plan.final_claim_template
        })
    
    # Step 2: Validate prerequisites
    print("Validating pre-requisite info:")
    prerequisite_nodes = []
    for i, prerequisite in enumerate(plan.prerequisites, 1):
        print(f"\nPrerequisite {i}/{len(plan.prerequisites)}: \"{prerequisite}\"")
        
        if progress_callback:
            progress_callback("prerequisite", f"Validating prerequisite {i}/{len(plan.prerequisites)}", {
                "index": i,
                "total": len(plan.prerequisites),
                "text": prerequisite,
                "status": "validating"
            })
        
        prereq_node = PrerequisiteNode(
            text=prerequisite,
            validation=ValidationStatus(status="validating")
        )
        
        # Get article for prerequisite
        print(f"-> LLM selects wikipedia article...")
        if progress_callback:
            progress_callback("prerequisite", f"Selecting Wikipedia article for prerequisite {i}...", {
                "index": i,
                "status": "selecting_article"
            })
        article_start = time.time()
        article_query = get_query_for_wiki_article(prerequisite)
        article_time = time.time() - article_start
        if not article_query:
            print(f"Failed to get article query for prerequisite")
            prereq_node.validation.status = "failed"
            prereq_node.validation.error = "Failed to get article query"
            prerequisite_nodes.append(prereq_node)
            if progress_callback:
                progress_callback("prerequisite", f"Failed to get article query for prerequisite {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        print(f"Article selected: \"{article_query}\" (took {article_time:.2f}s)")
        prereq_node.validation.article_query = article_query
        
        # Get or scrape article
        print(f"-> Fetching and scraping article...")
        if progress_callback:
            progress_callback("prerequisite", f"Fetching article: {article_query}", {
                "index": i,
                "article_query": article_query,
                "status": "fetching_article"
            })
        url, content = get_or_scrape_article(article_query, top_n_urls)
        if not content:
            print(f"Failed to scrape article for prerequisite")
            prereq_node.validation.status = "failed"
            prereq_node.validation.error = "Failed to scrape article"
            prerequisite_nodes.append(prereq_node)
            if progress_callback:
                progress_callback("prerequisite", f"Failed to scrape article for prerequisite {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        print(f"Article and scraped text key value pair stored into Scraped_Articles_Cache")
        print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}")
        
        # Fact check prerequisite
        print("-> Fact check is ran on prerequisite...")
        if progress_callback:
            progress_callback("prerequisite", f"Fact-checking prerequisite {i}...", {
                "index": i,
                "status": "factchecking"
            })
        factcheck_start = time.time()
        result = find_answer_in_article(content, prerequisite)
        factcheck_time = time.time() - factcheck_start
        if not result:
            print(f"Failed to fact-check prerequisite")
            prereq_node.validation.status = "failed"
            prereq_node.validation.error = "Failed to fact-check prerequisite"
            prerequisite_nodes.append(prereq_node)
            if progress_callback:
                progress_callback("prerequisite", f"Failed to fact-check prerequisite {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        print(f"Prerequisite result: {result.label}")
        print(f"Evidence: {result.evidence[:100]}..." if len(result.evidence) > 100 else f"Evidence: {result.evidence}")
        
        # Check if prerequisite is actually true
        if result.label == "True":
            prereq_node.validation.status = "validated"
            prereq_node.validation.label = result.label
            prereq_node.validation.evidence = result.evidence
            prereq_node.validation.article_url = url
            prereq_node.validation.link = build_text_fragment_link(url, result.evidence)
            
            prerequisite_nodes.append(prereq_node)
            
            print(f"Prerequisite {i} validated ✓")
            
            if progress_callback:
                progress_callback("prerequisite", f"Prerequisite {i} validated: {result.label}", {
                    "index": i,
                    "status": "validated",
                    "label": result.label
                })
        else:
            # Prerequisite is False - mark as failed and stop processing
            print(f"Prerequisite validation failed ({result.label}), cannot proceed")
            prereq_node.validation.status = "failed"
            prereq_node.validation.label = result.label
            prereq_node.validation.evidence = result.evidence
            prereq_node.validation.article_url = url
            prereq_node.validation.link = build_text_fragment_link(url, result.evidence)
            prereq_node.validation.error = f"Prerequisite validation failed: {result.label}"
            
            prerequisite_nodes.append(prereq_node)
            
            if progress_callback:
                progress_callback("prerequisite", f"Prerequisite {i} failed: {result.label}", {
                    "index": i,
                    "status": "failed",
                    "label": result.label
                })
            
            # Stop processing and mark final claim as failed
            if progress_callback:
                progress_callback("step", f"Prerequisite {i} failed. Cannot proceed with fact-checking.", {
                    "prerequisite_index": i,
                    "status": "failed"
                })
            
            # Return claim with failed prerequisite and failed final validation
            return ClaimNode(
                text=claim,
                prerequisites=prerequisite_nodes,
                additional_info=[],
                final_claim=None,
                final_validation=ValidationStatus(
                    status="failed",
                    error=f"Cannot proceed: Prerequisite {i} validation failed ({result.label})"
                )
            )
    
    if plan.prerequisites:
        print("\nAll prerequisites validated, proceed\n")
    
    # Step 3: Extract additional info
    extracted_info = {}
    additional_info_nodes = []
    
    if plan.additional_info_needed:
        print("Additional info required to validate? Yes:")
        
    for i, info_item in enumerate(plan.additional_info_needed, 1):
        print(f"\nExtracting info {i}/{len(plan.additional_info_needed)}: {info_item.purpose}")
        print(f"Question: \"{info_item.question}\"")
        
        if progress_callback:
            progress_callback("additional_info", f"Extracting info {i}/{len(plan.additional_info_needed)}: {info_item.purpose}", {
                "index": i,
                "total": len(plan.additional_info_needed),
                "purpose": info_item.purpose,
                "question": info_item.question,
                "status": "validating"
            })
        info_node = AdditionalInfoNode(
            purpose=info_item.purpose,
            question=info_item.question,
            validation=ValidationStatus(status="validating")
        )
        
        # Enhance question with previously extracted information
        enhanced_question = info_item.question
        if extracted_info:
            context_lines = [f"- {key}: {value}" for key, value in extracted_info.items()]
            context_str = "Previously extracted information:\n" + "\n".join(context_lines)
            enhanced_question = f"{info_item.question}\n\n{context_str}"
            print(f"Enhanced question with context: {extracted_info}")
        
        # Get article for question
        print(f"-> LLM selects wikipedia article...")
        if progress_callback:
            progress_callback("additional_info", f"Selecting article for info {i}...", {
                "index": i,
                "status": "selecting_article"
            })
        article_start = time.time()
        article_query = get_query_for_wiki_article(enhanced_question)
        article_time = time.time() - article_start
        if not article_query:
            print(f"Failed to get article query")
            info_node.validation.status = "failed"
            info_node.validation.error = "Failed to get article query"
            additional_info_nodes.append(info_node)
            if progress_callback:
                progress_callback("additional_info", f"Failed to get article query for info {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        print(f"Article selected: \"{article_query}\" (took {article_time:.2f}s)")
        info_node.validation.article_query = article_query
        
        # Get or scrape article
        cache_size_before = len(Scraped_Articles_Cache)
        if progress_callback:
            progress_callback("additional_info", f"Fetching article: {article_query}", {
                "index": i,
                "article_query": article_query,
                "status": "fetching_article"
            })
        url, content = get_or_scrape_article(article_query, top_n_urls)
        if not content:
            print(f"Failed to scrape article")
            info_node.validation.status = "failed"
            info_node.validation.error = "Failed to scrape article"
            additional_info_nodes.append(info_node)
            if progress_callback:
                progress_callback("additional_info", f"Failed to scrape article for info {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        cache_size_after = len(Scraped_Articles_Cache)
        if cache_size_after > cache_size_before:
            print(f"Article scraped and cached")
            print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}")
        else:
            print(f"Article already in cache, using cached content")
        
        info_node.validation.article_url = url
        
        # Extract answer from article
        print(f"-> Running question on article...")
        if progress_callback:
            progress_callback("additional_info", f"Extracting answer from article for info {i}...", {
                "index": i,
                "status": "extracting"
            })
        extract_start = time.time()
        answer = extract_answer_from_article(enhanced_question, content)
        extract_time = time.time() - extract_start
        if not answer or answer == "NOT_FOUND":
            print(f"Failed to extract answer")
            info_node.validation.status = "failed"
            info_node.validation.error = "Failed to extract answer"
            additional_info_nodes.append(info_node)
            if progress_callback:
                progress_callback("additional_info", f"Failed to extract answer for info {i}", {
                    "index": i,
                    "status": "failed"
                })
            continue
        
        print(f"LLM Returns \"{answer}\" (took {extract_time:.2f}s)")
        info_node.answer = answer
        info_node.validation.status = "validated"
        
        # Store evidence and create link to article
        # For additional info, the evidence is the answer itself, but we want to show it properly
        if answer and url:
            # Use the answer as evidence, but try to find a better context from the article
            # For now, use the answer as evidence
            info_node.validation.evidence = answer
            # Create a text fragment link pointing to the answer in the article
            info_node.validation.link = build_text_fragment_link(url, answer)
        
        extracted_info[info_item.purpose] = answer
        additional_info_nodes.append(info_node)
        
        if progress_callback:
            progress_callback("additional_info", f"Info {i} extracted: {answer[:50]}...", {
                "index": i,
                "status": "validated",
                "answer": answer,
                "evidence": answer,
                "article_url": url,
                "link": info_node.validation.link
            })
    
    # Step 4: Generate final claim
    print("\nFinal Claim to Check:")
    # First check if all prerequisites passed
    all_prerequisites_passed = all(
        p.validation.status == "validated" and p.validation.label == "True" 
        for p in prerequisite_nodes
    )
    
    if not all_prerequisites_passed:
        # Some prerequisites failed, mark final claim as failed
        print("Cannot generate final claim: prerequisites failed")
        if progress_callback:
            progress_callback("final_claim", "Cannot generate final claim: prerequisites failed", {
                "status": "failed"
            })
        return ClaimNode(
            text=claim,
            prerequisites=prerequisite_nodes,
            additional_info=additional_info_nodes,
            final_claim=None,
            final_validation=ValidationStatus(
                status="failed",
                error="Cannot proceed: One or more prerequisites failed validation"
            )
        )
    
    print("-> Use template and extracted info to generate a concise claim")
    if progress_callback:
        progress_callback("final_claim", "Generating final claim from template...", {"status": "generating"})
    final_claim_start = time.time()
    final_claim = generate_final_claim(claim, plan.final_claim_template, extracted_info)
    final_claim_time = time.time() - final_claim_start
    
    if final_claim:
        print(f"LLM generates: \"{final_claim}\" (took {final_claim_time:.2f}s)\n")
    
    if progress_callback and final_claim:
        progress_callback("final_claim", f"Final claim generated: {final_claim}", {
            "final_claim": final_claim,
            "status": "generated"
        })
    
    # Step 5: Final check
    print("Final Check Step:")
    final_validation = None
    if final_claim:
        final_validation = ValidationStatus(status="validating")
        
        print(f"-> Run fact check on claim")
        if progress_callback:
            progress_callback("final_claim", "Selecting article for final claim...", {"status": "selecting_article"})
        final_article_start = time.time()
        final_article_query = get_query_for_wiki_article(final_claim)
        final_article_time = time.time() - final_article_start
        if final_article_query:
            print(f"(article fetched will be {final_article_query})")
            final_validation.article_query = final_article_query
            
            cache_size_before = len(Scraped_Articles_Cache)
            if progress_callback:
                progress_callback("final_claim", f"Fetching article: {final_article_query}", {
                    "article_query": final_article_query,
                    "status": "fetching_article"
                })
            final_url, final_content = get_or_scrape_article(final_article_query, top_n_urls)
            
            cache_size_after = len(Scraped_Articles_Cache)
            if cache_size_after > cache_size_before:
                print(f"Article scraped and stored into cache")
                print(f"Cache now contains: {list(Scraped_Articles_Cache.keys())}\n")
            else:
                print(f"Article already in cache")
            
            if final_content:
                print("\n-> Running final fact check...")
                if progress_callback:
                    progress_callback("final_claim", "Fact-checking final claim...", {"status": "factchecking"})
                final_factcheck_start = time.time()
                final_result = find_answer_in_article(final_content, final_claim)
                final_factcheck_time = time.time() - final_factcheck_start
                
                if final_result:
                    print("\n=== Final Answer ===")
                    print(f"Label: {final_result.label}")
                    print(f"Evidence: {final_result.evidence}")
                    print("\n=== LINK TO RESPONSE ===")
                    link = build_text_fragment_link(final_url, final_result.evidence)
                    print(link)
                    
                    final_validation.status = "validated"
                    final_validation.label = final_result.label
                    final_validation.evidence = final_result.evidence
                    final_validation.article_url = final_url
                    final_validation.link = link
                    if progress_callback:
                        progress_callback("final_claim", f"Final claim validated: {final_result.label}", {
                            "status": "validated",
                            "label": final_result.label
                        })
                else:
                    print("Failed to get response for final claim")
                    final_validation.status = "failed"
                    final_validation.error = "Failed to fact-check final claim"
                    if progress_callback:
                        progress_callback("final_claim", "Failed to fact-check final claim", {"status": "failed"})
            else:
                print("Failed to scrape article for final claim")
                final_validation.status = "failed"
                final_validation.error = "Failed to scrape article for final claim"
                if progress_callback:
                    progress_callback("final_claim", "Failed to scrape article for final claim", {"status": "failed"})
        else:
            print("Failed to get article query for final claim")
            final_validation.status = "failed"
            final_validation.error = "Failed to get article query for final claim"
            if progress_callback:
                progress_callback("final_claim", "Failed to get article query for final claim", {"status": "failed"})
    
    return ClaimNode(
        text=claim,
        prerequisites=prerequisite_nodes,
        additional_info=additional_info_nodes,
        final_claim=final_claim,
        final_validation=final_validation
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    pass


app = FastAPI(
    title="The Truth Machine API",
    description="API for fact-checking claims against Wikipedia",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "The Truth Machine API"}


def generate_progress_stream(query: str, top_n_urls: int = 1) -> Generator[str, None, None]:
    """Generate a stream of progress updates as JSON strings."""
    start_time = time.time()
    
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print(f"{'=' * 60}\n")
    
    try:
        # Extract claims from query
        print("Extracting claims from query...")
        yield f"data: {json.dumps({'type': 'step', 'message': 'Extracting claims from query...', 'data': None})}\n\n"
        claims_start = time.time()
        claims = extract_claims_from_query(query)
        claims_time = time.time() - claims_start
        
        if not claims:
            print("No claims found to process")
            yield f"data: {json.dumps({'type': 'error', 'message': 'No claims found in query', 'data': None})}\n\n"
            return
        
        print(f"Extracted {len(claims)} claim(s) (took {claims_time:.2f}s):")
        for i, claim in enumerate(claims, 1):
            print(f"  {i}. {claim}")
        print()
        
        yield f"data: {json.dumps({'type': 'step', 'message': f'Found {len(claims)} claim(s) to process', 'data': {'claim_count': len(claims)}})}\n\n"
        
        # Process each claim
        claim_nodes = []
        for claim_idx, claim in enumerate(claims, 1):
            print(f"\n{'#' * 60}")
            print(f"Processing Claim {claim_idx}/{len(claims)}")
            print(f"{'#' * 60}")
            yield f"data: {json.dumps({'type': 'claim', 'message': f'Processing claim {claim_idx}/{len(claims)}', 'data': {'claim_index': claim_idx, 'total_claims': len(claims), 'claim_text': claim}})}\n\n"
            
            # Create a generator that yields updates and processes the claim
            def process_claim_generator():
                """Generator that processes claim and yields updates."""
                progress_updates = []
                
                def claim_progress_callback(update_type: str, message: str, data: Optional[Dict] = None):
                    update = {
                        'type': update_type,
                        'message': message,
                        'data': {**(data or {}), 'claim_index': claim_idx, 'claim_text': claim}
                    }
                    progress_updates.append(update)
                
                # Process the claim (this runs synchronously)
                claim_node = process_claim_with_plan_streaming(
                    claim, 
                    top_n_urls,
                    progress_callback=claim_progress_callback
                )
                
                # Yield all progress updates, then the result
                for update in progress_updates:
                    yield update
                
                yield {'type': 'claim_complete', 'claim_node': claim_node}
            
            # Process claim and yield updates as they come
            for update in process_claim_generator():
                if 'claim_node' in update:
                    claim_nodes.append(update['claim_node'])
                else:
                    yield f"data: {json.dumps(update)}\n\n"
            
            yield f"data: {json.dumps({'type': 'claim', 'message': f'Claim {claim_idx} completed', 'data': {'claim_index': claim_idx, 'status': 'completed'}})}\n\n"
        
        total_time = time.time() - start_time
        
        print(f"\n{'=' * 60}")
        print(f"Total time: {total_time:.2f}s")
        print(f"{'=' * 60}\n")
        
        # Send final result
        result = FactCheckResponse(
            query=query,
            claims=claim_nodes,
            total_time=total_time
        )
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Fact-checking completed', 'data': result.model_dump()})}\n\n"
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'data': None})}\n\n"


@app.post("/api/factcheck")
async def factcheck_query(request: QueryRequest):
    """Process a query and return structured fact-checking results (streaming)."""
    return StreamingResponse(
        generate_progress_stream(request.query, request.top_n_urls),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/factcheck-sync", response_model=FactCheckResponse)
async def factcheck_query_sync(request: QueryRequest):
    """Process a query and return structured fact-checking results (synchronous, non-streaming)."""
    start_time = time.time()
    
    try:
        # Extract claims from query
        claims = extract_claims_from_query(request.query)
        
        if not claims:
            return FactCheckResponse(
                query=request.query,
                claims=[],
                total_time=time.time() - start_time
            )
        
        # Process each claim
        claim_nodes = []
        for claim in claims:
            claim_node = process_claim_with_plan(claim, request.top_n_urls)
            claim_nodes.append(claim_node)
        
        total_time = time.time() - start_time
        
        return FactCheckResponse(
            query=request.query,
            claims=claim_nodes,
            total_time=total_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

