import scrapy
import logging
from scrapy.utils.log import configure_logging
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

configure_logging(install_root_handler=False)
logging.getLogger('scrapy').setLevel(logging.WARNING)
logging.getLogger('scrapy').propagate = False

class NjuskaloSpider(scrapy.Spider):
    name = "njuskalo"

    def __init__(self, urls=None, n_pages=1):
        self.n_pages = n_pages
        self.urls = []
        if urls:
            self.urls = urls

    def start_requests(self):
        for url in self.urls:
            yield scrapy.Request(url=url, callback=self.parse_page)

    def parse(self, response):
        def parse_price(label, currency_suffix):
            str_value = _css_get(response, f'.ClassifiedDetailSummary-price{label}::text')
            try:
                return int(
                    str_value.replace('.', '')
                             .replace(u'\xa0', '')
                             .replace(currency_suffix, '')
                )
            except:
                logging.error(f"Could not parse '{str_value}'")

        result = {
            'url': response.url,
            'title': _css_get(response, '.ClassifiedDetailSummary-title::text'),
            'price_hrk': parse_price('Domestic', 'kn'),
            'price_eur': parse_price('Foreign', u'€'),
            'id': _css_get(response, '.ClassifiedDetailSummary-adCode::text').replace('Šifra oglasa:', '').strip(),
            'publish_date': _get_publish_date(response),
        }
        table = _parse_table(response)
        result['total_area'] = table.get('Stambena površina', '')
        result['table_data'] = str(table)

        yield result

    def parse_page(self, response):
        # logging.debug('Parsing %s', response.url)
        for href in response.css(".EntityList-item--Regular .entity-title .link::attr(href)"):
            oglas_url = response.urljoin(href.extract())
            yield scrapy.Request(oglas_url, self.parse)

        for req in self._next_page(response):
            yield req

    def _next_page(self, response):
        next_page_button = response.css(".Pagination-item--next .Pagination-link::text")
        next_page_url, page_num = _next_page_url(response.url)

        if next_page_button and page_num <= self.n_pages:
            yield scrapy.Request(next_page_url, self.parse_page)


def _next_page_url(url):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    page_num = int(query_params.get('page', ['1'])[0]) + 1
    query_params['page'] = [page_num]

    new_query_string = urlencode(query_params, doseq=True)
    new_url = urlunsplit((scheme, netloc, path, new_query_string, fragment))

    return new_url, page_num


def _parse_table(response):
    table_values = response.css('.ClassifiedDetailBasicDetails-textWrapContainer')
    table_values = [_css_get(elem, '::text') for elem in table_values]

    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    table = {}
    for key, value in chunks(table_values, 2):
        table[key] = value
    return table


def _get_publish_date(response):
    data = response.css('.ClassifiedDetailSystemDetails-listData')
    if data:
        return _css_get(data[0], '::text')
    return ''


def _css_get(r, sel):
    selected = r.css(sel).extract()
    selected = filter(None, [x.strip() for x in selected])
    return ', '.join(selected)

