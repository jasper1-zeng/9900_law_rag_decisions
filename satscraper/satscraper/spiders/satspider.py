import scrapy
from satscraper.items import SATItem

class SatspiderSpider(scrapy.Spider):
    name = "satspider"
    allowed_domains = ["www.austlii.edu.au"]
    years = [str(year) for year in range(2022, 2026)]
    start_urls = [f"https://www.austlii.edu.au/cgi-bin/viewtoc/au/cases/wa/WASAT/{year}/" for year in years]
    
    # overwrite settings file
    custom_settings = {
        'FEEDS': {
            'satdata.json': {'format' : 'json', 'overwrite': True}
        }
    }

    def start_requests(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.austlii.edu.au/"
        }
        for url in self.start_urls:
            yield scrapy.Request(url, headers=headers, callback=self.parse)

    def parse(self, response):
        all_cases = response.css('div.card')
        for monthly_cases in all_cases:
            # Extract all relative urls
            relative_urls = monthly_cases.css('a::attr(href)').getall()

            for relative_url in relative_urls:
                case_url = response.urljoin(relative_url)

                yield response.follow(case_url, callback=self.parse_case_page, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.austlii.edu.au/"})

    def parse_case_page(self, response):
        sat_item = SATItem()
        
        case_url = response.url,
        case_title = response.css('article.the-document h1::text').get(default='')
        citation_number = response.css('a.autolink_findcases::text').get(default='').strip()

        ####################

        case_act = response.css('a.autolink_findacts::text').get(default='')
        if not case_act:
            case_act = response.xpath('//article[@class="the-document"]//p[b[contains(text(), "ACT")]]/text()').get(default='').strip()

        ####################
        member = response.xpath('//article[@class="the-document"]//b[contains(text(), "MEMBER")]/following-sibling::text()').get(default='').strip()
        heard_date = response.xpath('//article[@class="the-document"]//b[contains(text(), "HEARD")]/following-sibling::text()').get(default='').strip()
        delivery_date = response.xpath('//article[@class="the-document"]//b[contains(text(), "DELIVERED")]/following-sibling::text()').get(default='').strip()
        file_no = response.xpath('//article[@class="the-document"]//b[contains(text(), "FILE NO/S")]/following-sibling::text()').get(default='').strip()
        
        ####################
        # Extract case_between
        case_between = ""
        between_start = response.xpath('//b[contains(text(), "BETWEEN")]')
        if between_start:
            # Try position-based extraction first
            between_idx = response.xpath('count(//b[contains(text(), "BETWEEN")]/preceding::*)').get()
            
            # Find possible end boundaries by looking ahead for catchwords
            catchwords_idx = None
            
            # Check for named anchor
            anchor_idx = response.xpath('count(//a[@name="CatchwordsText"]/preceding::*)').get()
            if anchor_idx:
                catchwords_idx = anchor_idx
            
            # Check for italicized Catchwords label
            if not catchwords_idx:
                italic_idx = response.xpath('count(//p[i[contains(text(), "Catchwords:")]]/preceding::*)').get()
                if italic_idx:
                    catchwords_idx = italic_idx
            
            # Check for connected phrases with hyphens
            if not catchwords_idx:
                # Look for paragraphs with multiple " - " separators (characteristic of catchwords)
                hyphen_idx = response.xpath('count(//p[string-length(.) > 50 and contains(., " - ") and contains(substring-after(., " - "), " - ")]/preceding::*)').get()
                if hyphen_idx:
                    catchwords_idx = hyphen_idx
            
            # Extract using position boundaries if both are found
            if between_idx and catchwords_idx:
                case_between = " ".join(
                    response.xpath(f'//node()[count(preceding::*) > {between_idx} and count(preceding::*) < {catchwords_idx}]/text()').getall()
                ).strip()
            
            # Fallback to limited original approach if position-based extraction fails
            if not case_between:
                case_between = " ".join(
                    response.xpath(
                        '//b[contains(text(), "BETWEEN")]/parent::p//text() | '
                        '//b[contains(text(), "BETWEEN")]/parent::p/following-sibling::*[position() < 5]/descendant-or-self::text()'
                    ).getall()
                ).strip()
        
        ####################

        catchwords = " ".join(response.xpath('//a[@name="CatchwordsText"]/ancestor::p/descendant-or-self::text()').getall()).strip()
        if not catchwords:
            catchwords = " ".join(response.xpath("//p[i[contains(text(), 'Catchwords:')]]//text()").getall()).strip()

        legislations = " ".join(response.xpath('//a[@name="LegislationText"]/ancestor::p/descendant-or-self::text()').getall()).strip()
        if not legislations:
            legislations = " ".join(response.xpath("//p[i[contains(text(), 'Legislation:')]]//text()").getall()).strip()

        result = "\n".join(
            response.xpath(
                '''
                (
                //i[contains(text(), "Result:")]/ancestor::p[1] |
                //i[contains(text(), "Result:")]/ancestor::p[1]/following-sibling::p[
                    not(i[contains(text(), "Category:")]) and 
                    not(preceding-sibling::p[i[contains(text(), "Category:")]])
                ]
                )//text()
                '''
            ).getall()
        ).strip()
        category = response.xpath('//p[i[contains(text(), "Category")]]/text()').get(default='').strip()
        
        ####################

        # '//b[contains(text(), "Representation")]/parent::p/following-sibling::*[not(self::p[a[@name="CasesReferred"]]) and not(preceding-sibling::p[a[@name="CasesReferred"]]) and preceding-sibling::p[b[contains(text(), "Representation")]]]/descendant-or-self::text()'
        representation = "".join(
                    response.xpath(
                        '//b[contains(text(), "Representation")]/parent::p/following-sibling::*[not(self::p[b[contains(text(), "Case(s) referred to in decision(s):")]]) and not(preceding-sibling::p[b[contains(text(), "Case(s) referred to in decision(s):")]]) and preceding-sibling::p[b[contains(text(), "Representation")]]]/descendant-or-self::text()'
                    ).getall()
                ).strip()

        # Start with a very permissive selector to capture the referred cases section
        referred_cases = ""

        # Try to find the start and end points of referred cases section
        start_node = response.xpath('//b[contains(text(), "Case") and contains(text(), "referred")]').get()
        if start_node:
            # Get all paragraphs between the header and the next major heading
            para_texts = response.xpath('//b[contains(text(), "Case") and contains(text(), "referred")]/ancestor::p/following-sibling::p[not(.//b[contains(text(), "REASONS")])]/descendant-or-self::text()').getall()
            
            # Join the texts into a single string
            referred_cases = "\n".join(para_texts).strip()

        # If nothing found, try a more permissive approach with a specific search for the format in your example
        if not referred_cases:
            # Look for the specific name="CasesReferred" anchor
            referred_cases = "\n".join(
                response.xpath('//a[@name="CasesReferred"]/following::p[not(ancestor::p[.//b[contains(text(), "REASONS")]])]/descendant-or-self::text()').getall()
            ).strip()

        # Last resort - try to extract everything between "Cases referred" and "REASONS"
        if not referred_cases:
            # Get the index of the "Cases referred" node
            cases_node_idx = response.xpath('count(//b[contains(text(), "Case") and contains(text(), "referred")]/preceding::*)').get()
            reasons_node_idx = response.xpath('count(//b[contains(text(), "REASONS")]/preceding::*)').get()
            
            if cases_node_idx and reasons_node_idx:
                # Get all text nodes between these two indices
                referred_cases = "\n".join(
                    response.xpath(f'//node()[count(preceding::*) > {cases_node_idx} and count(preceding::*) < {reasons_node_idx}]/text()').getall()
                ).strip()
        
        ####################
    
        # Try to find reasons for decision with more flexible approach
        reasons = "\n".join(
            response.xpath(
                '//b[contains(normalize-space(.), "REASONS FOR DECISION")]/following::*//text()'
            ).getall()
        ).strip()
        # The case where HTML for older years has different format
        if not reasons:
            reasons = "\n".join(
                response.xpath(
                    '//b[contains(normalize-space(.), "REASONS FOR THE DECISION")]/following::*//text()'
                ).getall()
            ).strip()
        # Handle blockquote format where "REASONS FOR DECISION" comes after member name
        if not reasons:
            reasons = "\n".join(
                response.xpath(
                    '//blockquote[.//b[contains(normalize-space(.), "REASONS FOR DECISION")]]/following::*//text()'
                ).getall()
            ).strip()
        # Handle blockquote format where "REASONS FOR DECISION" comes before member name
        if not reasons:
            reasons = "\n".join(
                response.xpath(
                    '//blockquote[.//b[contains(text(), "MEMBER") or contains(text(), "JUDGE")]]/following::*//text()'
                ).getall()
            ).strip()
        
        ####################
        
        sat_item['case_url'] = case_url[0]
        sat_item['case_title'] = case_title if case_title else 'N/A'
        sat_item['citation_number'] = citation_number if citation_number else 'N/A'
        sat_item['case_year'] = citation_number[1:5] if citation_number else 'N/A'
        sat_item['case_act'] = case_act if case_act else 'N/A'
        sat_item['member'] = member if member else 'N/A'
        sat_item['heard_date'] = heard_date if heard_date else 'N/A'
        sat_item['delivery_date'] = delivery_date if delivery_date else 'N/A'
        sat_item['file_no'] = file_no if file_no else 'N/A'
        sat_item['case_between'] = case_between if case_between else 'N/A'
        sat_item['catchwords'] = catchwords if catchwords else 'N/A'
        sat_item['legislations'] = legislations if legislations else 'N/A'
        sat_item['result'] = result if result else 'N/A'
        sat_item['category'] = category if category else 'N/A'
        sat_item['representation'] = representation if representation else 'N/A'
        sat_item['referred_cases'] = referred_cases if referred_cases else 'N/A'
        sat_item['reasons'] = reasons if reasons else 'N/A'

        yield sat_item