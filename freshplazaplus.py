# -*- coding: utf-8 -*-
import scrapy
import lxml.html
import datetime
import urlparse
from data_fetchers.items import DataFetchersItem
from scrapy.selector import Selector
from data_fetchers import utils
from data_fetchers.spider import get_text
from data_fetchers.spider import Spider


class FreshPlazaPlusSpider(Spider):
    name = "freshplazaplus"
    source_crawler = 'freshplaza'
    crawl_type = 'news'
    version = 1
    allowed_domains = []
    start_urls = [
        'http://www.freshplaza.com/',
    ]
    all_urls = set()

    def parse_item(self, response):
        item = self.get_new_item(response)
        item['json']['listitem'] = response.meta['listitem']
        try:
            article = response.xpath("//div[@id='bericht']")
        except UnicodeDecodeError:
            article = Selector(text=unicode(response.body,"ISO-8859-1")).xpath("//div[@id='bericht']")

        summaryOriginal = "".join(article.extract()).strip()
        summarySelector = Selector(text=summaryOriginal)
        if not summaryOriginal:
            return
        lxmlTree = lxml.html.fromstring(summaryOriginal)
        image_infos = []
        image_urls = []
        images = summarySelector.xpath('//img')
        for image in images:
            image_src = urlparse.urljoin(item['json']['listitem']['source_url'], image.xpath(".//@src").extract()[0].strip())
            if image.xpath(".//@alt"):
                image_alt = image.xpath(".//@alt").extract()[0].strip()
            elif image.xpath(".//@title"):
                image_alt = image.xpath(".//@title").extract()[0].strip()
            else:
                image_alt = None
            image_infos.append((image_src,image_alt))
        caption_images = {}
        for image_info in image_infos:
            image_url, image_alt = image_info
            caption_images[image_url] = (None,image_alt)
            image_urls.append(image_url)

        item['image_urls'] = image_urls
        item["json"]["caption_images"] = caption_images
        sourceNode = summarySelector.xpath("//p[text()='Source: ']/following::a")
        if sourceNode:
            if sourceNode.xpath('./@href'):
                item['json']['end_source_url'] = sourceNode.xpath('./@href').extract()[0]
                item['json']['end_source'] = sourceNode.xpath('./text()').extract()[0]
            delLinkNode = lxmlTree.xpath("//p[text()='Source: ']/following::a")[0]
            delLinkNode.getparent().remove(delLinkNode)
            delSourceNode = lxmlTree.xpath("//p[text()='Source: ']")[0]
            delSourceNode.getparent().remove(delSourceNode)

        dateNode = summarySelector.xpath("//p[starts-with(.,'Publication date: ')]")
        if dateNode:
            item['json']['date'] = dateNode.xpath('./text()').extract()[0].replace('Publication date: ', '').strip()
            delDateNode = lxmlTree.xpath("//p[starts-with(.,'Publication date: ')]")[0]
            delDateNode.getparent().remove(delDateNode)

        shareNode=summarySelector.xpath("//div[contains(@class,'addthis_toolbox')]")
        if shareNode:
            delShareNode = lxmlTree.xpath("//div[contains(@class,'addthis_toolbox')]")[0]
            delShareNode.getparent().remove(delShareNode)

        summary = lxml.html.tostring(lxmlTree, encoding="UTF-8")
        del lxmlTree

        item['json']['content'] = summary
        item['json']['title'] = get_text("".join(article.xpath(".//span[@class='kop']").extract()).strip())
        if "categories" in item['json']['listitem']:
            item["json"]["categories"] = item['json']['listitem']["categories"]
        item['thumb_urls'] = item['json']['listitem']['thumb_urls']
        item["json"]["item_url"] = item['json']['listitem']['source_url']
        item['html'] = response.body
        htmls_path = {
            item['json']['listitem']['source_url']:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = item['json']['listitem']['source_url']

        return item

    @staticmethod
    def check_existance_additional(item):
        res = False
        return res

    def parse_list(self, response):
        self.log('========= list is list page! %s' % response.url)

        items = []
        main = response.css('#hoofdartikelen p[class!="datum"][class!="kop"]')
        left = response.css('#sectoren_links p[class!="kop"]')
        right = response.css('#sectoren_rechts p[class!="kop"]')
        targets = main + left + right
        for newsitem in targets:
            item = {}
            full_url = newsitem.xpath('.//a/@href').extract()
            if full_url:
                full_url = full_url[0]
            else:
                continue
            item["categories"] = [response.meta["category"]]
            item['source_url'] = full_url
            item['title'] = newsitem.css('span.kop::text').extract()
            item['thumb_urls'] = [urlparse.urljoin(response.url,image_url) for image_url in newsitem.xpath('.//img/@src').extract() if image_url]
            item['source_crawler'] = self.source_crawler
            if not self.check_existance(sourceCrawler=item['source_crawler'],
                                        sourceURL=item['source_url'],
                                        items_scraped=self.items_scraped) and \
                    item['source_url'] not in self.all_urls:
                self.all_urls.add(item['source_url'])
                items.append(item)
            else:
                self.log('the news has scraped already')

        for item in items:
            yield scrapy.Request(item['source_url'], callback=self.parse_item, dont_filter=True, meta={'listitem': item})

    def parse(self,response):
        category_labels = response.xpath("//div[contains(@id,'sectormenu')]/ul/li/a")
        for category_label in category_labels:
            meta = {}
            label_url = urlparse.urljoin(response.url,category_label.xpath(".//@href").extract()[0].strip())
            if "www.freshplaza.com" not in label_url:
                continue
            meta["category"] = category_label.xpath(".//text()").extract()[0].strip()
            yield scrapy.Request(label_url, callback=self.parse_list, dont_filter=True, meta=meta)
