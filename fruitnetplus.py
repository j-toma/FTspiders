# -*- coding: utf-8 -*-
import scrapy
import urlparse
import gc
import datetime
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from lxml.html import fromstring, tostring
from itertools import chain
from data_api.models import Crawl
from data_fetchers.spider import Spider
from scrapy.selector import Selector


class FruitNetPlusSpider(Spider):
    name = 'fruitnetplus'
    source_crawler = 'fruit_net'
    crawl_type = 'news'
    item_parser="parse_article"
    version = 1
    allowed_domains = []
    start_urls = (
        'http://www.fruitnet.com/eurofruit',
        'http://www.fruitnet.com/asiafruit',
        'http://www.fruitnet.com/americafruit',
        'http://www.fruitnet.com/produceplus',
        'http://www.fruitnet.com/fpj',
        'http://www.fruitnet.com/freshconvenience',
    )
    has_scraped_uris = []

    def parse_authors(self, response):
        item = response.meta['item']
        json = item['json']
        authors = {}
        if response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/img"):
            authors['authors_img_link'] = response.xpath("//div[@class='tab_heading author']/div[@class='author_column']/img/@src").extract()[0].strip()
        if response.xpath("//div[@class='tab_heading author']/h3/text()"):
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
        item["htmls_path"][response.meta["authors_url"]] = response.body
        return item

    def parse_article(self, response):
        self.log('this is an item page! %s' % response.url)
        url_contains = "nizhaobudaowo"
        if response.url:
            uris = response.url.split("/")
            url_contains = "%s/%s" % (uris[5],uris[6])
        if url_contains not in self.has_scraped_uris:
            self.has_scraped_uris.append(url_contains)
            html = utils.decode(response.body)
            item = self.get_new_item(response)
            json = item["json"]
            json['item_url'] = response.url
            if 'category' in response.meta:
                json['category'] = response.meta['category']
            if 'tags' in response.meta:
                json['tags'] = response.meta['tags']
            thumb_urls = []
            if 'thumb_urls' in response.meta:
                thumb_urls += response.meta['thumb_urls']
            item['thumb_urls'] = thumb_urls
            if response.xpath("//div[@class='main']/article[@id='article']/h1[@itemprop='name']"):
                json['title'] = response.xpath("//div[@class='main']/article[@id='article']/h1[@itemprop='name']/text()").extract()[0].strip()
            if response.xpath("//div[@class='main']/article[@id='article']/p[@class='date']"):
                json['date'] = response.xpath("//div[@class='main']/article[@id='article']/p[@class='date']/text()").extract()[0].strip()
            if response.xpath("//div[@class='main']/article[@id='article']/h2[@class='standfirst']"):
                json['excerpt'] = response.xpath("//div[@class='main']/article[@id='article']/h2[@class='standfirst']/text()").extract()[0].strip()

            image_urls = []
            caption_images = {}
            article = response.xpath("//article[contains(@id,'article')]").extract()[0].strip()
            article_document = fromstring(article)
            if article_document.xpath(".//div[contains(@class,'actions')]"):
                del_actions = article_document.xpath(".//div[contains(@class,'actions')]")[0]
                del_actions.getparent().remove(del_actions)
            if article_document.xpath(".//p[contains(@itemprop,'datePublished')]"):
                del_date = article_document.xpath(".//p[contains(@itemprop,'datePublished')]")[0]
                del_date.getparent().remove(del_date)
            if article_document.xpath(".//h1[contains(@itemprop,'name')]"):
                del_title = article_document.xpath(".//h1[contains(@itemprop,'name')]")[0]
                del_title.getparent().remove(del_title)
            if article_document.xpath(".//h2[contains(@itemprop,'description')]"):
                del_desc = article_document.xpath(".//h2[contains(@itemprop,'description')]")[0]
                del_desc.getparent().remove(del_desc)
            if article_document.xpath(".//div[contains(@class,'article_tabs')]"):
                del_tabs = article_document.xpath(".//div[contains(@class,'article_tabs')]")[0]
                del_tabs.getparent().remove(del_tabs)
            if article_document.xpath(".//img[contains(@class,'article_image')]"):
                article_body = article_document.xpath(".//div[contains(@itemprop,'articleBody')]")[0]
                for article_image in article_document.xpath(".//img[contains(@class,'article_image')]"):
                    src = urlparse.urljoin(response.url,article_image.xpath(".//@src")[0].encode("UTF-8"))
                    if article_image.xpath(".//@alt"):
                        alt = article_image.xpath(".//@alt")[0].encode("UTF-8")
                    elif article_image.xpath(".//@title"):
                        alt = article_image.xpath(".//@title")[0].encode("UTF-8")
                    else:
                        alt = None
                    if article_image.xpath(".//parent::a") and\
                       Selector(text=tostring(article_image.xpath(".//parent::a")[0], encoding="UTF-8")).xpath(".//@title"):
                        caption = Selector(text=tostring(article_image.xpath(".//parent::a")[0], encoding="UTF-8")).xpath(".//@title").extract()[0].strip()
                    else:
                        caption= None
                    caption_images[src] = (caption,alt)
                    image_urls.append(src)
                    article_body.addprevious(article_image)
            if article_document.xpath(".//div[contains(@class,'letterbox_image_wrapper')]"):
                del_cf = article_document.xpath(".//div[contains(@class,'letterbox_image_wrapper')]")[0]
                del_cf.getparent().remove(del_cf)
            if article_document.xpath(".//div[contains(@class,'article_right_col')]"):
                del_ar = article_document.xpath(".//div[contains(@class,'article_right_col')]")[0]
                del_ar.getparent().remove(del_ar)

            image_infos = []
            if response.xpath(".//div[contains(@itemprop,'articleBody')]/descendant::img[@src]"):
                for image in response.xpath(".//div[contains(@itemprop,'articleBody')]/descendant::img[@src]"):
                    image_src = urlparse.urljoin(response.url, image.xpath(".//@src").extract()[0].strip())
                    if image.xpath(".//@alt"):
                        image_alt = image.xpath(".//@alt").extract()[0].strip()
                    elif image.xpath(".//@title"):
                        image_alt = image.xpath(".//@title").extract()[0].strip()
                    else:
                        image_alt = None
                    image_infos.append((image_src,image_alt))
            for image_info in image_infos:
                image_url,image_alt = image_info
                caption_images[image_url] = (None,image_alt)
                image_urls.append(image_url)
            item['image_urls'] = image_urls
            json["caption_images"] = caption_images

            json['content'] = tostring(article_document, encoding="UTF-8")
            item['json'] = json
            item['html'] = html
            htmls_path = {
                response.meta['source_url']:response.body
            }
            item["htmls_path"] = htmls_path
            item['source_url'] = response.meta['source_url']
            authors_url = ''
            if response.xpath("//div[@id='article_author']/descendant::a[@class='author_link']"):
                authors_url = urlparse.urljoin(response.url, response.xpath("//div[@id='article_author']/descendant::a[@class='author_link']/@href").extract()[0].strip())
            if authors_url:
                yield scrapy.Request(authors_url, callback=self.parse_authors, dont_filter=True, meta={'item': item, "authors_url": authors_url})
            else:
                yield item
        else:
            self.log('the item has scraped already! %s' % response.url)

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
                thumb_urls = urlparse.urljoin(url, thumb_urls)
                param['thumb_urls'] = [thumb_urls]
            if listItem.xpath(".//h4/a"):
                listItemUrl = urlparse.urljoin(url, listItem.xpath(".//h4/a/@href").extract()[0].strip())
            param['source_url'] = listItemUrl
            if listItem.xpath(".//p[@class='sub']/span/following-sibling::a"):
                tags = []
                for item_tag in listItem.xpath(".//p[@class='sub']/span/following-sibling::a"):
                    tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(), urlparse.urljoin(url, item_tag.xpath(".//@href").extract()[0].strip()))
                    tags.append(tagTuple)
                param['tags'] = tags
            url_contains = "nizhaobudaowo"
            if listItemUrl:
                uris = listItemUrl.split("/")
                url_contains = "%s/%s" % (uris[5],uris[6])
            if not self.check_existance(
                    sourceCrawler=self.source_crawler,
                    sourceURL=listItemUrl,
                    items_scraped=self.items_scraped) and not \
                    Crawl.objects.filter(source_crawler=self.source_crawler,source_url__icontains=url_contains).exists() and \
                    url_contains not in self.has_scraped_uris:
                yield scrapy.Request(listItemUrl, callback=self.parse_article, dont_filter=True, meta=param)
            else:
                self.log('the item has scraped already! %s' % listItemUrl)
        gc.collect()

    def parse(self, response):
        url = response.url
        self.log('this is a plus page! %s' % url)
        products = response.xpath("//nav[@id='main_nav']/ul/li")[0]
        topics = response.xpath("//nav[@id='main_nav']/ul/li")[1]
        countries = response.xpath("//nav[@id='main_nav']/ul/li")[2]
        for category_list in chain(products.xpath(".//ul[contains(@class,'menu')]//a"), topics.xpath(".//ul[contains(@class,'menu')]//a"), countries.xpath(".//ul[contains(@class,'menu')]//a")):
            list_url = urlparse.urljoin(url, category_list.xpath(".//@href").extract()[0].strip())
            list_category = category_list.xpath(".//text()").extract()[0].strip()
            yield scrapy.Request(list_url, callback=self.parse_list, dont_filter=True, meta={'category': list_category})
        gc.collect()
