# -*- coding: utf-8 -*-
import scrapy
import gc
import datetime
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from lxml.html import fromstring, tostring
from data_fetchers.spider import Spider


class GrowingProduceSpider(Spider):
    name = 'GrowingProduce'
    source_crawler = 'growing_produce'
    crawl_type = 'news'
    version = 1
    allowed_domains = ['www.growingproduce.com']
    start_urls = (
        'http://www.growingproduce.com/vegetables',
        'http://www.growingproduce.com/fruits',
        'http://www.growingproduce.com/nuts',
        'http://www.growingproduce.com/citrus',
    )
    hasCrawledTags = set()
    all_urls = set()

    def parse_item(self, response):
        self.log('this is an item page! %s' % response.url)
        html = utils.decode(response.body)
        item = DataFetchersItem()
        json = {}
        json['item_url'] = response.url
        if "reparse_from" in response.meta:
            json["reparse_from"] = response.meta["reparse_from"]
        if self.is_reparse:
            if 'category' in response.meta["json"]:
                category = response.meta["json"]['category']
                json['category'] = category
            json['title'] = response.meta["json"]['title']
            json['date'] = response.meta["json"]['date']
            json['excerpt'] = response.meta["json"]['excerpt']
            thumb_urls = []
            if 'thumb_urls' in response.meta["json"]:
                thumb_urls += response.meta["json"]['thumb_urls']
        else:
            if 'category' in response.meta:
                category = response.meta['category']
                json['category'] = category
            json['title'] = response.meta['title']
            json['date'] = response.meta['date']
            json['excerpt'] = response.meta['excerpt']
            thumb_urls = []
            if 'thumb_urls' in response.meta:
                thumb_urls += [response.meta['thumb_urls']]
        item['thumb_urls'] = thumb_urls
        tags = []
        for item_tag in response.xpath("//section[@class='tags']/span[@itemprop='keywords']/a[@rel='tag']"):
            tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(), item_tag.xpath(".//@href").extract()[0].strip())
            tags.append(tagTuple)
        json['tags'] = tags
        if response.xpath("//div[contains(@class,'date-author-wrap')]/descendant::a[@rel='author']"):
            # author_url = response.xpath("//div[contains(@class,'date-author-wrap')]/descendant::a[@rel='author']")
            json['author'] = response.xpath("//div[contains(@class,'date-author-wrap')]/descendant::a[@rel='author']/span/text()").extract()[0].strip()
        res = utils.readability(html=html)
        summaryOriginal = res['content']
        lxmlTree = fromstring(summaryOriginal)
        image_urls = []
        for url in lxmlTree.xpath("//section[@class='body']/descendant::img[@src]/@src"):
            image_urls += [url.encode("UTF-8")]
        item['image_urls'] = image_urls
        caption_images = {}
        for image_url in image_urls:
            caption_images["image_url"] = None
        json["caption_images"] = caption_images
        json['content'] = tostring(lxmlTree.xpath("//section[@class='body']")[0], encoding="UTF-8")
        del lxmlTree
        item['json'] = json
        item['html'] = html
        htmls_path = {
            response.meta['source_url']:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = response.meta['source_url']
        item['source_crawler'] = self.source_crawler
        item['crawl_type'] = self.crawl_type
        item['created_time'] = datetime.datetime.now()
        yield item
        for tagKey, tagValue in tags:
            if tagKey not in self.hasCrawledTags:
                self.hasCrawledTags.add(tagKey)
                yield scrapy.Request(tagValue, callback=self.parse_list, dont_filter=True)
        gc.collect()

    def parse_list(self, response):
        self.log('this is a list page: %s' % response.url)
        listItems = response.xpath("//div[contains(@class,'taxonomy-listing')]/div[contains(@class,'item')]")
        for listItem in listItems:
            param = {}
            listItemUrl = ''
            if listItem.xpath(".//div[@class='image']"):
                param['thumb_urls'] = listItem.xpath(".//div[@class='image']/a/img/@src").extract()[0].strip()
                param['category'] = listItem.xpath(".//div[@class='image']/div[contains(@class,'category-tag')]/a/text()").extract()[0].strip()
            if listItem.xpath(".//div[@class='meta']"):
                listItemUrl = listItem.xpath(".//div[@class='meta']/a[contains(@class,'title')]/@href").extract()[0].strip()
                param['title'] = listItem.xpath(".//div[@class='meta']/a[contains(@class,'title')]/text()").extract()[0].strip()
                param['date'] = listItem.xpath(".//div[@class='meta']/div[@class='date']/text()").extract()[0].strip()
                param['excerpt'] = listItem.xpath(".//div[@class='meta']/div[@class='excerpt']/text()").extract()[0].strip()
                param['source_url'] = listItemUrl
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=listItemUrl,
                                        items_scraped=self.items_scraped) and \
                    listItemUrl not in self.all_urls:
                self.all_urls.add(listItemUrl)
                yield scrapy.Request(listItemUrl, callback=self.parse_item, dont_filter=True, meta=param)
            else:
                self.log('the item has scraped already! %s' % listItemUrl)
        gc.collect()

    def parse(self, response):
        url = response.url
        self.log('this is a category page! %s' % url)
        if response.xpath("//div[@class='not-phone']/descendant::ul[@class='page-numbers']"):
            which_li = len(response.xpath("//div[@class='not-phone']/descendant::ul[@class='page-numbers']/li")) - 2
            this_li = response.xpath("//div[@class='not-phone']/descendant::ul[@class='page-numbers']/li")[which_li]
            page_size = int(this_li.xpath(".//a/text()").extract()[0])
            for i in range(1, page_size + 1):
                for_url = response.url + 'page/%s' % i
                self.log('list request page: %s' % for_url)
                yield scrapy.Request(for_url, callback=self.parse_list, dont_filter=True)
        else:
            yield scrapy.Request(url, callback=self.parse_list, dont_filter=True)
        gc.collect()
