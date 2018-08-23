# -*- coding: utf-8 -*-
import scrapy
import urlparse
import gc
import datetime
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from lxml.html import fromstring, tostring
from itertools import chain
from data_fetchers.spider import Spider


class FruitNetSpiderOld(Spider):
    name = 'fruitnet'
    source_crawler = 'fruit_net'
    crawl_type = 'news'
    item_parser = "parse_article"
    version = 1
    allowed_domains = ['www.fruitnet.com']
    start_urls = (
        'http://www.fruitnet.com/eurofruit',
        'http://www.fruitnet.com/asiafruit',
        'http://www.fruitnet.com/americafruit',
        'http://www.fruitnet.com/produceplus',
        'http://www.fruitnet.com/fpj',
        'http://www.fruitnet.com/freshconvenience',
    )
    all_urls = set()

    def parse_authors(self, response):
        item = response.meta['item']
        json = item['json']
        authors = {}
        if response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/img"):
            authors['authors_img_link'] = response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/img/@src").extract()[0].strip()
        if response.xpath("//div[@class='tab_heading author']/h3"):
            authors['authors_name'] = response.xpath("//div[@class='tab_heading author']/h3/text()").extract()[0].strip()
        if response.xpath("//div[@class='tab_heading author']/div[@class='description']"):
            description = ''
            for p in response.xpath("//div[@class='tab_heading author']/div[@class='description']/p"):
                description += p.xpath(".//text()").extract()[0].strip()
            authors['authors_description'] = description
        if response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='email']"):
            authors['authors_email'] = response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='email']/@href").extract()[0].strip().split(":")[1].replace("(at)", "@").replace("(dot)", ".")
        if response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='twitter']"):
            authors['authors_twitter'] = response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='twitter']/@href").extract()[0].strip()
        if response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='tel']"):
            authors['authors_tel'] = response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/a[@class='tel']/text()").extract()[0].strip()
        json['authors'] = authors
        item['json'] = json
        item["htmls_path"][response.url] = response.body
        return item

    def parse_article(self, response):
        self.log('this is an item page! %s' % response.url)
        html = utils.decode(response.body)
        item = DataFetchersItem()
        json = {}
        if "reparse_from" in response.meta:
            json["reparse_from"] = response.meta["reparse_from"]
        json['item_url'] = response.url
        if self.is_reparse:
            if 'category' in response.meta["json"]:
                json['category'] = response.meta["json"]['category']
            if 'tags' in response.meta["json"]:
                json['tags'] = response.meta["json"]['tags']
            thumb_urls = []
            if 'thumb_urls' in response.meta["json"]:
                thumb_urls += response.meta["json"]['thumb_urls']
        else:
            if 'category' in response.meta:
                json['category'] = response.meta['category']
            if 'tags' in response.meta:
                json['tags'] = response.meta['tags']
            thumb_urls = []
            if 'thumb_urls' in response.meta:
                thumb_urls += [response.meta['thumb_urls']]

        item['thumb_urls'] = thumb_urls
        if response.xpath("//div[@class='main']/article[@id='article']/h1[@itemprop='name']"):
            json['title'] = response.xpath("//div[@class='main']/article[@id='article']/h1[@itemprop='name']/text()").extract()[0].strip()
        if response.xpath("//div[@class='main']/article[@id='article']/p[@class='date']"):
            json['date'] = response.xpath("//div[@class='main']/article[@id='article']/p[@class='date']/text()").extract()[0].strip()
        if response.xpath("//div[@class='main']/article[@id='article']/h2[@class='standfirst']"):
            json['excerpt'] = response.xpath("//div[@class='main']/article[@id='article']/h2[@class='standfirst']/text()").extract()[0].strip()
        image_urls = []
        if response.xpath("//article[@id='article']/descendant::img[@src]"):
            for url in response.xpath("//article[@id='article']/descendant::img[@src]"):
                image_urls += [urlparse.urljoin(response.url, url.xpath(".//@src").extract()[0].strip())]
        item['image_urls'] = image_urls
        caption_images = {}
        for image_url in image_urls:
            caption_images[image_url] = None
        json["caption_images"] = caption_images
        res = utils.readability(html=html)
        summaryOriginal = res['content']
        if 'title' not in json and res['title']:
            json['title'] = res['title']
        lxmlTree = fromstring(summaryOriginal)
        if lxmlTree.xpath("//div[@id='article_body']"):
            json['content'] = tostring(lxmlTree.xpath("//div[@id='article_body']")[0], encoding="UTF-8")
        else:
            json['content'] = tostring(lxmlTree.xpath("//div")[0], encoding="UTF-8")
        del lxmlTree
        item['json'] = json
        item['html'] = html
        htmls_path = {
            response.meta["source_url"]:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = response.meta["source_url"]
        item['source_crawler'] = self.source_crawler
        item['crawl_type'] = self.crawl_type
        item['created_time'] = datetime.datetime.now()
        authors_url = ''
        if response.xpath("//div[@id='article_author']/descendant::a[@class='author_link']"):
            authors_url = urlparse.urljoin(response.url, response.xpath("//div[@id='article_author']/descendant::a[@class='author_link']/@href").extract()[0].strip())
        if authors_url:
            yield scrapy.Request(authors_url, callback=self.parse_authors, dont_filter=True, meta={'item': item})
        else:
            yield item
        gc.collect()

    def parse_list(self, response):
        url = response.url
        category = response.meta['category']
        self.log('this is a list page: %s' % url)
        listItems = response.xpath("//ul[@id='articles_list']/li")
        for listItem in listItems:
            param = {}
            param['category'] = category
            listItemUrl = ''
            if listItem.xpath(".//a[@class='img thumb']/@style"):
                thumb_urls = listItem.xpath(".//a[@class='img thumb']/@style").extract()[0].strip().split("'")[1]
                if thumb_urls and 'http' not in thumb_urls[:4]:
                    thumb_urls = urlparse.urljoin(url, thumb_urls)
                param['thumb_urls'] = thumb_urls
            if listItem.xpath(".//h4/a"):
                listItemUrl = urlparse.urljoin(url, listItem.xpath(".//h4/a/@href").extract()[0].strip())
            param['source_url'] = listItemUrl
            if listItem.xpath(".//p[@class='sub']/span/following-sibling::a"):
                tags = []
                for item_tag in listItem.xpath(".//p[@class='sub']/span/following-sibling::a"):
                    tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(), urlparse.urljoin(url, item_tag.xpath(".//@href").extract()[0].strip()))
                    tags.append(tagTuple)
                param['tags'] = tags
            #
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=listItemUrl,
                                        items_scraped=self.items_scraped) and \
                    listItemUrl not in self.all_urls:
                self.all_urls.add(listItemUrl)
                yield scrapy.Request(listItemUrl, callback=self.parse_article, dont_filter=True, meta=param)
            else:
                self.log('the item has scraped already! %s' % listItemUrl)
        gc.collect()

    def parse_page_list(self, response):
        url = response.url
        category = response.meta['category']
        self.log('this is a page list: %s' % url)
        pageNum = 0
        if response.xpath("//ul[@class='article_filters']/li[contains(@class,'paginate')]/ol[@class='cf']/li[contains(@class,'last')]"):
            pageNum = int(response.xpath("//ul[@class='article_filters']/li[contains(@class,'paginate')]/ol[@class='cf']/li[contains(@class,'last')]/a/text()").extract()[0].strip())
        if pageNum:
            for i in range(1, pageNum + 1):
                page_list_url = url + "/page/" + str(i)
                yield scrapy.Request(page_list_url, callback=self.parse_list, dont_filter=True, meta={'category': category})
        else:
            yield scrapy.Request(url, callback=self.parse_list, dont_filter=True, meta={'category': category})
        gc.collect()

    def parse(self, response):
        url = response.url
        self.log('this is a global page! %s' % url)
        products = response.xpath("//nav[@id='main_nav']/ul/li")[0]
        topics = response.xpath("//nav[@id='main_nav']/ul/li")[1]
        countries = response.xpath("//nav[@id='main_nav']/ul/li")[2]
        for category_list in chain(products.xpath(".//ul[contains(@class,'menu')]//a"), topics.xpath(".//ul[contains(@class,'menu')]//a"), countries.xpath(".//ul[contains(@class,'menu')]//a")):
            list_url = urlparse.urljoin(url, category_list.xpath(".//@href").extract()[0].strip())
            list_category = category_list.xpath(".//text()").extract()[0].strip()
            yield scrapy.Request(list_url, callback=self.parse_page_list, dont_filter=True, meta={'category': list_category})
        gc.collect()
