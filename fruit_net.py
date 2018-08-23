# -*- coding: utf-8 -*-
import scrapy
import urlparse
from itertools import chain
from lxml.html import fromstring, tostring
from data_fetchers.spider import Spider
from data_api.models import Crawl
from data_fetchers import utils
from scrapy.selector import Selector


class FruitNetSpider(Spider):
    name = "fruit_net"
    source_crawler = "fruit_net"
    crawl_type = "news"
    version = 3
    crawl_mode = "PLUS"  # ALL
    allowed_domains = []
    start_urls = (
        'http://www.fruitnet.com/eurofruit',
        'http://www.fruitnet.com/asiafruit',
        'http://www.fruitnet.com/americafruit',
        'http://www.fruitnet.com/produceplus',
        'http://www.fruitnet.com/fpj',
        'http://www.fruitnet.com/freshconvenience',
    )
    has_crawled = set()

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

    def parse_item(self, response):
        html = utils.decode(response.body)
        item = self.get_new_item(response)
        json = item["json"]
        json['item_url'] = response.url
        if 'categories' in response.meta:
            json['categories'] = response.meta['categories']
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

    def parse_list(self,response):
        url = response.url
        category = response.meta["category"]
        list_items = response.xpath("//ul[contains(@id, 'articles_list')]/li")
        for list_item in list_items:
            param = {}
            item_url = ""
            if list_item.xpath(".//h4/a"):
                item_url = urlparse.urljoin(
                    url,
                    list_item.xpath(".//h4/a/@href").extract()[0].strip()
                )
            if not item_url:
                continue
            param['source_url'] = item_url
            if list_item.xpath(".//a[contains(@class, 'thumb')]/@style"):
                thumb_urls = urlparse.urljoin(
                    url,
                    list_item.xpath(
                        ".//a[contains(@class, 'thumb')]/@style"
                    ).extract()[0].strip().split("'")[1]
                )
                param['thumb_urls'] = [thumb_urls]
            categories_tag = list_item.xpath(
                ".//p[@class='sub']/span/following-sibling::a"
            )
            if categories_tag:
                categories = []
                for category_tag in categories_tag:
                    categories.append(
                        category_tag.xpath(".//text()").extract()[0].strip()
                    )
                if category not in categories:
                    categories.append(category)
                param["categories"] = categories
            uri = "/".join(item_url.split("/")[-2:])
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=item_url,
                                        items_scraped=self.items_scraped) and \
                    uri not in self.has_crawled:
                self.has_crawled.add(uri)
                yield scrapy.Request(
                    item_url,
                    callback=self.parse_item,
                    dont_filter=True,
                    meta=param
                )

    def parse_page_list(self, response):
        crawled = False
        url = response.url
        category = response.meta["category"]
        yield scrapy.Request(
            url,
            callback=self.parse_list,
            dont_filter=True,
            meta={"category": category}
        )
        if self.crawl_mode == "PLUS":
            article_tags = response.xpath(
                "//ul[contains(@id, 'articles_list')]/li"
            )
            article_urls = [urlparse.urljoin(
                url, article_tag.xpath(".//h4/a/@href").extract()[0].strip()
            ) for article_tag in article_tags]
            article_uris = ["/".join(article_url.split("/")[-2:])
                            for article_url in article_urls]
            crawled_count = Crawl.objects.filter(
                source_crawler=self.source_crawler,
                source_url__in=article_urls
            ).count()
            if crawled_count == 0:
                ratio_db = 0
            else:
                ratio_db = float(crawled_count) / len(article_tags)
            if len(self.has_crawled.intersection(set(article_uris))) == 0:
                ratio_gv = 0
            else:
                ratio_gv = float(
                    len(self.has_crawled.intersection(set(article_uris)))
                ) / len(article_tags)
            if article_tags and (ratio_db > 0.5 or ratio_gv > 0.5):
                crawled = True
        next_page_tag = response.xpath("//li[contains(@class, 'next')]/a")
        if next_page_tag and not crawled:
            next_page_list_url = urlparse.urljoin(
                url, next_page_tag.xpath(".//@href").extract()[0].strip()
            )
            yield scrapy.Request(
                next_page_list_url,
                callback=self.parse_page_list,
                dont_filter=True,
                meta={"category": category}
            )

    def parse(self, response):
        url = response.url
        nav_doc = fromstring(response.xpath(
            "//nav[contains(@id,'main_nav')]"
        ).extract()[0].strip())
        products_doc = nav_doc.xpath(".//a[text()='Products']")[0].getnext()
        topics_doc = nav_doc.xpath(".//a[text()='Topics']")[0].getnext()
        countries_doc = nav_doc.xpath(".//a[text()='Countries']")[0].getnext()
        iter_chain = chain(
            products_doc.xpath(".//a"),
            topics_doc.xpath(".//a"),
            countries_doc.xpath(".//a")
        )
        for category in iter_chain:
            category_name = unicode(category.xpath(".//text()")[0])
            category_url = urlparse.urljoin(
                url,
                unicode(category.xpath(".//@href")[0])
            )
            yield scrapy.Request(
                category_url,
                callback=self.parse_page_list,
                dont_filter=True,
                meta={"category": category_name}
            )
