# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from scrapy.selector import Selector
from lxml.html import fromstring, tostring
from data_fetchers.spider import Spider


class FDARecallsSpider(Spider):
    name = "FDARecalls"
    source_crawler = 'FDA_Recall'
    crawl_type = 'recall'
    item_parser="parse_detail"
    version = 1
    allowed_domains = []
    start_urls = (
        'http://www.fda.gov/Safety/Recalls/default.htm',
    )
    all_urls = set()

    def parse_item(self, response):
        item = response.meta['item']
        image_infos = []
        image_urls = []
        for image in response.xpath("//div[@class='row content']/descendant::img[@src]"):
            image_src = urlparse.urljoin(response.url, image.xpath(".//@src").extract()[0].strip())
            if image.xpath(".//@alt"):
                image_alt = image.xpath(".//@alt").extract()[0].strip()
            elif image.xpath(".//@title"):
                image_alt = image.xpath(".//@title").extract()[0].strip()
            else:
                image_alt = None
            image_infos.append((image_src,image_alt))
        caption_images = {}
        for image_info in image_infos:
            image_url,image_alt = image_info
            caption_images[image_url] = (None,image_alt)
            image_urls.append(image_url)
        item['image_urls'] = image_urls
        item['json']["caption_images"] = caption_images
        item["htmls_path"][response.meta["item_url"]] = response.body
        return item

    def parse_detail(self, response):
        self.log('this is an item page! %s' % response.url)
        item = self.get_new_item(response)
        item['json']['date'] = response.meta['date']
        item['json']['brand_name'] = response.meta['brand_name']
        item['json']['product_description'] = response.meta['product_description']
        item['json']['reason_problem'] = response.meta['reason_problem']
        item['json']['company'] = response.meta['company']
        sourceurl = response.meta["source_url"]

        article = response.xpath("//article").extract()[0].strip()
        item['json']['title'] = response.xpath("//title/text()").extract()[0].strip()
        lxmlTree = fromstring(article)
        if lxmlTree.xpath("//article/h3[1]"):
            dangerTitle = lxmlTree.xpath("//article/h3[1]")[0]
            dangerTitle.getparent().remove(dangerTitle)
        if lxmlTree.xpath("//article/p[1]"):
            dangerContent = lxmlTree.xpath("//article/p[1]")[0]
            dangerContent.getparent().remove(dangerContent)
        title = []
        if 'title' not in item and lxmlTree.xpath("//article/h1"):
            h1_tmp = tostring(lxmlTree.xpath("//article/h1")[0], encoding="UTF-8")
            h1_start = h1_tmp.find('>') + 1
            h1_end = h1_tmp.find('</')
            item['json']['title'] = h1_tmp[h1_start:h1_end]
            title = lxmlTree.xpath("//h1")[0]
            title.getparent().remove(title)
        elif 'title' not in item and lxmlTree.xpath("//article/h2"):
            h2_tmp = tostring(lxmlTree.xpath("//article/h2")[0], encoding="UTF-8")
            h2_start = h2_tmp.find('>') + 1
            h2_end = h2_tmp.find('</')
            item['json']['title'] = h2_tmp[h2_start:h2_end]
            title = lxmlTree.xpath("//article/h2")[0]
            title.getparent().remove(title)
        elif 'title' not in item and lxmlTree.xpath("//article/h3"):
            h3_tmp = tostring(lxmlTree.xpath("//article/h3")[0], encoding="UTF-8")
            h3_start = h3_tmp.find('>') + 1
            h3_end = h3_tmp.find('</')
            item['json']['title'] = h3_tmp[h3_start:h3_end]
            title = lxmlTree.xpath("//article/h3")[0]
            title.getparent().remove(title)
        else:
            pass
        item_url = ''
        for element in lxmlTree.xpath("//article/p"):
            text = ''
            if element.xpath(".//text()"):
                text = element.xpath(".//text()")[0].strip()
            if 'Photo:' in text:
                item_url = urlparse.urljoin(response.url, element.xpath(".//a/@href")[0].strip())
            if not text \
                or text == '###' \
                or 'RSS Feed for FDA Recalls Information' in text \
                or 'Photo: Product Labels' in text \
                    or 'Recalled Product Photos Are Also Available on FDA' in text:
                element.getparent().remove(element)

        contentProcess = tostring(lxmlTree, encoding="UTF-8")
        spSelector = Selector(text=contentProcess)
        item['json']['content'] = spSelector.xpath("//article").extract()[0]
        item['html'] = response.body
        htmls_path = {
            sourceurl:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = sourceurl
        if item_url:
            yield scrapy.Request(item_url,
                                 callback=self.parse_item,
                                 dont_filter=True,
                                 meta={'item': item, "item_url": item_url})
        else:
            item['image_urls'] = []
            yield item

    def parse(self, response):
        self.log('this is a list page! %s' % response.url)
        items = response.xpath("//tbody/tr")
        for item in items:
            if item.xpath('.//td'):
                date, brand_name, product_description, reason_problem, company, _, _ = item.xpath('.//td')
                meta = {
                    'date': date.xpath(".//text()").extract()[0].strip(),
                    'brand_name': brand_name.xpath(".//a/text()").extract()[0].strip(),
                    'product_description': product_description.xpath(".//text()").extract()[0].strip(),
                    'reason_problem': reason_problem.xpath(".//text()").extract()[0].strip(),
                    'company': company.xpath(".//text()").extract()[0].strip()}
                item_url = urlparse.urljoin(response.url, brand_name.xpath(".//a/@href").extract()[0].strip())
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=item_url,
                                            items_scraped=self.items_scraped) and \
                        item_url not in self.all_urls:
                    self.all_urls.add(item_url)
                    meta["source_url"] = item_url
                    yield scrapy.Request(item_url,
                                         callback=self.parse_detail,
                                         dont_filter=True,
                                         meta=meta)
                else:
                    self.log('the news has scraped already! %s' % item_url)
