import "dotenv/config";
import fetch from "node-fetch";
import * as cheerio from "cheerio";
import OpenAI from "openai";

const API_KEY = process.env.CUSTOM_SEARCH_API_KEY;
const CX = process.env.CUSTOM_SEARCH_ENGINE_ID;

const client = new OpenAI();

async function getFirstNTResultsUrls(query, n) {
  const url = new URL("https://www.googleapis.com/customsearch/v1");
  url.searchParams.set("key", API_KEY);
  url.searchParams.set("cx", CX);
  url.searchParams.set("q", query);

  const res = await fetch(url);
  const data = await res.json();
  return data.items?.slice(0, n).map((item) => item.link) || null;
}

async function scrapeWikipediaContent(url) {
  try {
    const response = await fetch(url);
    const html = await response.text();
    const $ = cheerio.load(html);

    // Remove unwanted elements
    $(
      ".navbox, .infobox, .sidebar, .reference, .mw-editsection, .mw-jump-link, .toc, .catlinks, .mw-cite-backlink"
    ).remove();

    // Get the main content from the Wikipedia article
    const content = $("#mw-content-text .mw-parser-output");

    // Extract text from paragraphs, headings, and lists
    const textContent = [];

    content.find("h1, h2, h3, h4, h5, h6, p, li").each((i, element) => {
      const text = $(element).text().trim();
      if (text && text.length > 10) {
        // Filter out very short text
        textContent.push(text);
      }
    });

    return textContent.join("\n\n");
  } catch (error) {
    console.error("Error scraping content:", error);
    return null;
  }
}

async function findAnswerInArticle(scrapedContent, claim) {
  try {
    const response = await client.responses.create({
      model: "gpt-5-nano",
      input: `Based on the following scraped content from a web page, please print the exact text from the content that verifies or disproves the claim provided. Ensure selected text is concise and only contains relevant info to either prove or disprove the claim. Return a single string of text strictly from the article scraped, and ensure its no more than a couple sentences long.  Claim: "${claim}"\n\nScraped Content:\n${scrapedContent}`,
    });

    return response.output_text || "No response from GPT";
  } catch (error) {
    console.error("Error calling GPT API:", error);
    return null;
  }
}

async function extractClaimsFromQuery(query) {
  try {
    const response = await client.responses.create({
      model: "gpt-5-nano",
      input: `Strictly extract claims and facts that could be fact-checked from the following query. Return the claims as a JSON array of strings. If no claims are present, such as strict questions, return an empty array: "${query}"`,
    });

    const claims = JSON.parse(response.output_text || "[]");
    return claims;
  } catch (error) {
    console.error("Error calling GPT API:", error);
    return [];
  }
}

async function optimizeClaim(claim) {
  try {
    const response = await client.responses.create({
      model: "gpt-5-mini",
      input: `Rewrite the following claim such that the core assertion of the claim can be easily fact checked in a relevant article without requiring addtional context. Return a single optimized claim. Claim: ${claim}`,
    });

    return response.output_text || "No response from GPT";
  } catch (error) {
    console.error("Error calling GPT API:", error);
    return null;
  }
}

async function getQueryForWikiArticle(claim) {
  try {
    const response = await client.responses.create({
      model: "gpt-5-nano",
      input: `Return the name of the wikipedia article that contains the answer to the claim "${claim}"`,
    });

    return response.output_text || "No response from GPT";
  } catch (error) {
    console.error("Error calling GPT API:", error);
    return null;
  }
}

(async () => {
  let query = "Gustavo fring in brba was chilean and his actor was brazilian";

  let claims = await extractClaimsFromQuery(query);
  console.log("Claims:", claims);

  for (const claim of claims) {
    console.log("\n\nEvaluating claim:", claim);

    console.log("Optimized claim: ", await optimizeClaim(claim));

    let queryForWikiArticle = await getQueryForWikiArticle(claim);
    console.log("Wikipedia Article To Check:", queryForWikiArticle);

    let urls = await getFirstNTResultsUrls(queryForWikiArticle, 1);
    console.log("URLs Fetched:", urls);

    if (urls) {
      console.log("\nScraping content from Wikipedia article...");
      const content = await scrapeWikipediaContent(urls[0]);

      if (content) {
        const gptResponse = await findAnswerInArticle(content, claim);

        if (gptResponse) {
          console.log("\n=== Answer from article ===");
          console.log(gptResponse);
        } else {
          console.log("Failed to get response from GPT");
        }

        console.log("\n=== LINK TO RESPONSE ===");
        const encodedText = encodeURIComponent(gptResponse);
        console.log(urls[0] + "#:~:text=" + encodedText);
      } else {
        console.log("Failed to scrape content from the URL");
      }
    } else {
      console.log("No URL found from search");
    }
  }
})();
