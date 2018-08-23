# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers import utils
from data_fetchers.spider import Spider
from data_fetchers.items import DataFetchersItem
from lxml.html import fromstring, tostring


class ProduceBusinessUK(Spider):
    name = 'producebusinessuk'
    source_crawler = 'producebusinessuk'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['www.producebusinessuk.com']
    start_urls = ['http://www.producebusinessuk.com/purchasing/stories'
                  'http://www.producebusinessuk.com/supply/stories',
                  'http://www.producebusinessuk.com/insight/insight-stories',
                  'http://www.producebusinessuk.com/marketing-pr/marketing-pr-stories',
                  'http://www.producebusinessuk.com/services/stories',
                  'http://www.producebusinessuk.com/academia/stories']
    all_urls = set()

    def parse(self,response):
        params = {}
        articles = response.xpath("//li[@class=\"item\"]")
        if articles:
            for article in articles:
                title = article.xpath(".//h2/a/text()")
                if title:
                    params['title'] = title.extract()[0]
                date = article.xpath(".//strong/text()")
                if date:
                    params['date'] = date.extract()[0]
                thumb = article.xpath(".//img/@src")
                if thumb:
                    params['thumb'] = thumb.extract()[0]
                article_url = urlparse.urljoin(response.url,article.xpath(".//h2/a/@href|.//div/a/@href").extract()[0])
                if article_url:
                    if not self.check_existance(sourceCrawler='producebusinessuk',
                                                sourceURL=article_url,
                                                items_scraped=self.items_scraped) and article_url not in self.all_urls:
                        self.all_urls.add(article_url)
                        yield scrapy.Request(
                            article_url,
                            callback=self.parse_article,
                            dont_filter=True,
                            meta=params)

        # pages = response.xpath("//div[contains(@id,'Content_C001')]/a/@href")
        # if pages:
        #     for page in pages:
        #         page_url = page.extract()
        #         if page_url:
        #             yield scrapy.Request(page_url,callback=self.parse,dont_filter=True)

    def parse_article(self,response):
        item = self.get_new_item()
        item['source_url'] = response.url
        item['html'] = response.body
        item["htmls_path"] = {response.url:response.body}
        item['created_time'] = datetime.datetime.now()
        item['thumb_urls'] = [response.meta['thumb']] if response.meta['thumb'] else []
        item['image_urls'] = []
        item['json'] = {}
        item['json']['title'] = response.meta['title'] if response.meta['title'] else ""
        item['json']['date'] = response.meta['date'] if response.meta['date'] else ""

        content = ''.join(response.xpath("//article").extract()).strip()
        lxml_content = fromstring(content)
        image_urls = []
        caption_images = {}

        # del shit
        del_title = lxml_content.xpath(".//h1")
        if del_title is not None:
            del_title = del_title[0]
            del_title.getparent().remove(del_title)

        del_author = lxml_content.xpath(".//div[contains(@class,'author')]")
        if del_author is not None:
            del_author = del_author[0]
            del_author.getparent().remove(del_author)

        del_date = lxml_content.xpath(".//time")
        if del_date is not None:
            del_date = del_date[0]
            del_date.getparent().remove(del_date)

        del_share = lxml_content.xpath(".//div[contains(@class,'addthis')]")
        if del_share is not None:
            del_share = del_share[0]
            del_share.getparent().remove(del_share)

        del_back = lxml_content.xpath("./a")
        if del_back is not None:
            del_back = del_back[0]
            del_back.getparent().remove(del_back)

        del_prev = lxml_content.xpath("./p")
        if del_prev is not None:
            del_prev = del_prev[0]
            del_prev.getparent().remove(del_prev)

        del_comment = lxml_content.xpath("./div/@id/..")
        if del_comment is not None:
            del_comment = del_comment[0]
            del_comment.getparent().remove(del_comment)

        # gallery
        owls = lxml_content.xpath("//div[contains(@class,'photo-gallery')]")
        for owl in owls:
            image_divs = owl.xpath(".//div[@class=\'item\']")
            for image_div in image_divs:
                image_url = image_div.xpath(".//img/@src")[0]
                image_urls.append(image_url)
                figcaption = image_div.xpath(".//div/text()")[0]
                caption_images[image_url] = (figcaption,item['json']['title'] if 'title' in item['json'] else "")
                owl.addnext(image_div.xpath(".//img")[0])
            owl.getparent().remove(owl)

        # stage image (non gallery)
        stage = lxml_content.xpath(".//div[@class=\'article-stage']")
        if stage:
            stage = stage[0]
            img = stage.xpath("./img/@src")
            if img:
                img_url = img[0]
                img_cap = stage.xpath("./p[@class=\'article-caption\']/text()")
                if img_url not in image_urls:
                    caption_images[img_url] = (img_cap[0],item['json']['title'] if 'title' in item['json'] else "")
                    image_urls.append(img_url)
            keep_img = stage.xpath(".//img")[0]
            stage.addnext(keep_img)
            stage.getparent().remove(stage)

        # image in article
        figure = lxml_content.xpath(".//div/figure")
        if figure:
            figure = figure[0]
            img = figure.xpath(".//img/@src")
            if img:
                img_url = img[0]
                img_cap = figure.xpath(".//figcaption/text()")
                if img_url not in image_urls:
                    caption_images[img_url] = (img_cap[0],item['json']['title'] if 'title' in item['json'] else "")
                    image_urls.append(img_url)
            keep_img = figure.xpath(".//img")[0]
            figure.addnext(keep_img)
            figure.getparent().remove(figure)

        if image_urls is not None:
            item['image_urls'] = image_urls
        if caption_images is not None:
            item['json']['captioned_images'] = caption_images
        item['json']['content'] = tostring(lxml_content,encoding='utf-8')
        yield item
