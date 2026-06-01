# Intelligence Report Requirements

You have access to the API response data in `api_response.json`. 
The API endpoint is: `https://apiprod.mtygs.cn/api/posts/v2/queryIntelligenceUpToDate`

## Task
Write a Python script `generate_report.py` that:
1. Reads the JSON data from `api_response.json`  
2. Classifies each item into one of these macro categories based on content analysis:
   - **大盘/宏观** (Macro): items about central bank, interest rates, CPI, PPI, GDP, monetary policy, fund flows
   - **行业/产业** (Industry): items about sector trends, industry data, supply chain updates
   - **个股/公司** (Stock/Company): items about specific companies, earnings, products, orders
3. Groups items by date (YYYY-MM-DD) 
4. Generates a structured Markdown report saved as `report.md`

## Report Format Requirements
The report must include:
- A title with the date range covered
- A statistics summary section showing total count and breakdown by date and category
- Content organized by date (newest first), with sub-sections by category
- Each item should show: category tag, time, and content (truncated to 150 chars max)
- A "Key Highlights" section at the top listing the 5 most-viewed items across all dates
