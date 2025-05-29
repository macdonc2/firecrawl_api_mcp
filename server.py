import os
import logging
from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from firecrawl import FirecrawlApp, ScrapeOptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("firecrawl_mcp")

client_request_timeout = float(
    os.getenv("MCP_CLIENT_REQUEST_TIMEOUT", "30.0")
)

# Initialize MCP server via FastMCP
mcp = FastMCP(
    name="Firecrawl MCP",
    instructions="Call firecrawl_search, firecrawl_scrape, or firecrawl_crawl. "
                 "Supply your Firecrawl API key as 'Authorization: Bearer fc-…' header.",
    sse_path="/firecrawl_api/sse",
    message_path="/firecrawl_api/messages/"
)

def _get_api_key() -> str:
    """
    Extracts the Firecrawl API key from the current HTTP Authorization header.

    Returns:
        str: The Firecrawl API bearer token.

    Raises:
        Exception: If the Authorization header is missing, malformed, 
                   or the token format is invalid.

    Note: 
        This was a pain to get right!
    """

    headers = get_http_headers()  # pulls headers from current SSE context
    auth = headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        logger.error("Authorization header missing or malformed")
        raise Exception("Authorization header missing or malformed")
    token = auth.split(" ", 1)[1]
    if not token.startswith("fc-"): # Specific to Firecrawl.  Not really needed.
        logger.error("Invalid Firecrawl API token format")
        raise Exception("Invalid Firecrawl API token format")
    return token

# Tools for the MCP server (FirecrawlApp methods)
@mcp.tool(name="firecrawl_search")
def firecrawl_search(
    query: str,
    limit: int = 5 # Agent can determine how many results to return if prompted.
) -> List[dict]:
    """
    Searches Firecrawl using the provided query and returns a list of search results.

    Args:
        query (str): The search query to be executed.
        limit (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        List[dict]: A list of search result dictionaries.

    Raises:
        Exception: If the search fails or there is an error in the API call.
    """

    token = _get_api_key()
    logger.info(f"firecrawl_search(query={query!r}, limit={limit})")
    client = FirecrawlApp(api_key=token)
    try:
        resp = client.search(query=query, limit=limit)
        results = getattr(resp, "data", resp) or []
        logger.info(f"search returned {len(results)} results")
        # optionally peek at first 3 entries for efficiency - may want to remove.
        for i, item in enumerate(results[:3], start=1):
            logger.info(f"  result {i}: {item}")
        return results
    except Exception as e:
        logger.exception("firecrawl_search failed")
        raise Exception(f"Firecrawl search failed: {e}")

@mcp.tool(name="firecrawl_scrape")
def firecrawl_scrape(
    url: str,
    formats: Optional[List[str]] = ['markdown', 'html'],
    only_main_content: bool = True,
    wait_for: Optional[int] = None,
    timeout: Optional[int] = None,
) -> dict:
    """
    Scrapes a web page using Firecrawl and returns the content in the specified formats.

    Args:
        url (str): The target URL to scrape.
        formats (Optional[List[str]]): List of formats to return; defaults to ['markdown', 'html'].
        only_main_content (bool): If True, scrapes only the main content. Defaults to True.
        wait_for (Optional[int]): Time in milliseconds to wait for page load before scraping.
        timeout (Optional[int]): Maximum scraping duration in milliseconds.

    Returns:
        dict: The scraped page content in the specified formats.

    Raises:
        Exception: If scraping fails or there is an error in the API call.
    """

    token = _get_api_key()
    logger.info(
        f"firecrawl_scrape(url={url!r}, formats={formats}, "
        f"only_main_content={only_main_content}, wait_for={wait_for}, timeout={timeout})"
    )
    client = FirecrawlApp(api_key=token)
    opts = {}
    if formats is not None:
        opts["formats"] = formats
    opts["onlyMainContent"] = only_main_content
    if wait_for is not None:
        opts["waitFor"] = wait_for
    if timeout is not None:
        opts["timeout"] = timeout

    try:
        return client.scrape_url(url, **opts)
    except Exception as e:
        logger.exception("firecrawl_scrape failed")
        raise Exception(f"Firecrawl scrape failed: {e}")

@mcp.tool(name="firecrawl_crawl")
def firecrawl_crawl(
    url: str,
    limit: int = 10,
    max_depth: Optional[int] = None,
) -> dict:
    """
    Crawls a website starting from the given URL using Firecrawl and returns the crawl results.

    Args:
        url (str): The starting URL for the crawl.
        limit (int): Maximum number of pages to crawl. Defaults to 10.
        max_depth (Optional[int]): Maximum depth to crawl. If None, uses default depth.

    Returns:
        dict: The crawl results containing scraped content and metadata.

    Raises:
        Exception: If the crawl fails or the API call encounters an error.
    """

    token = _get_api_key()
    logger.info(f"firecrawl_crawl(url={url!r}, limit={limit}, max_depth={max_depth})")
    client = FirecrawlApp(api_key=token)
    crawl_opts = {"limit": limit}
    if max_depth is not None:
        crawl_opts["maxDepth"] = max_depth
    crawl_opts["scrapeOptions"] = ScrapeOptions(formats=["markdown", "html"])

    try:
        return client.crawl_url(url, **crawl_opts)
    except Exception as e:
        logger.exception("firecrawl_crawl failed")
        raise Exception(f"Firecrawl crawl failed: {e}")

# Entrypoint via FastMCP
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    logger.info(f"Starting Firecrawl MCP SSE on 0.0.0.0:{port}")
    mcp.run(transport="sse", host="0.0.0.0", port=port)
