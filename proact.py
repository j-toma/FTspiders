import scrapy
import urlparse
import datetime
from cStringIO import StringIO
from data_fetchers.spider import Spider
from data_fetchers import utils
from data_fetchers.items import DataFetchersItem
from pdfminer.layout import LAParams
from pdfminer.image import ImageWriter
from pdfminer.converter import HTMLConverter, TextConverter
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage


outtype = 'html'
codec = 'utf-8'
password = ''
scale = 1
layoutmode = 'normal'
laparams = LAParams()
pagenos = set()
maxpages = 0
caching = True
imagewriter = None
rotation = 0
rsrcmgr = PDFResourceManager(caching=caching)


def process_pdf(f):
    outfile = StringIO()
    device = HTMLConverter(rsrcmgr, outfile, codec=codec, scale=scale,
                           layoutmode=layoutmode, laparams=laparams,
                           imagewriter=imagewriter)
    # device = TextConverter(rsrcmgr, outfile, codec=codec, laparams=laparams,
    #                        imagewriter=imagewriter)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in PDFPage.get_pages(f, pagenos,
                                  maxpages=maxpages, password=password,
                                  caching=caching, check_extractable=True):
        page.rotate = (page.rotate+rotation) % 360
        outfile.write(interpreter.process_page(page))
    device.close()
    return outfile


class ProAct(Spider):
    name = 'proact'
    source_crawler = 'proact'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://www.proactusa.com']
    start_urls = ['http://www.proactusa.com/wp-content/uploads/2014/',
                  'http://www.proactusa.com/wp-content/uploads/2015/']
    all_urls = set()

    def parse(self,response):
        months = response.xpath("//li[not(contains(a,'Parent Directory'))]")
        if months:
            for month in months:
                month_url = urlparse.urljoin(response.url,month.xpath(".//a/@href").extract()[0])
                yield scrapy.Request(month_url,callback=self.parse_month,dont_filter=True)

    def parse_month(self,response):
        articles = response.xpath("//li[contains(a,'TheOutlook')]|//li[contains(a,'TheSource')]")
        if articles:
            for article in articles:
                article_url = urlparse.urljoin(response.url,article.xpath(".//a/@href").extract()[0])
                if not self.check_existance(sourceCrawler='proact',
                                            sourceURL=article_url,
                                            items_scraped=self.items_scraped) and article_url not in self.all_urls:
                    self.all_urls.add(article_url)
                    yield scrapy.Request(
                        article_url,
                        callback=self.parse_article,
                        dont_filter=True)

    def parse_article(self,response):
        item = self.get_new_item()
        item['source_url'] = response.url
        item['html'] = response.body
        item["htmls_path"] = {response.url:response.body}
        item['created_time'] = datetime.datetime.now()
        item['thumb_urls'] = []
        item['image_urls'] = []
        item['json'] = {}

        infile = StringIO(response.body)
        content = process_pdf(infile).getvalue()
        item['json']['content'] = content

        yield item
