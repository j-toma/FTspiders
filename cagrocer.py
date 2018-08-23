# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
import copy
from data_fetchers import utils
from lxml.html import fromstring, tostring


class Cagrocers(Spider):

    name = 'cagrocers_news'
    source_crawler = "cagrocers"
    crawl_type = "news"
    version = 0
    allowed_domains = ['www.cagrocers.com']
    start_urls = [
        "http://www.cagrocers.com/communications/news/"
    ]
    all_url = set()

    def parse(self, response):

        for element in response.xpath('//article[@class=\"entry-content clearfix\"]/div[@class=\"newsArticle\"]'):

            # source url
            url = ''.join(element.xpath('.//a[@class=\"greenText\"]/@href').extract()).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)

            meta = {
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler='cagrocers',
                                        sourceURL=source_url,
                                        items_scraped=self.items_scraped)\
                    and source_url not in self.all_url:
                self.all_url.add(source_url)

                yield scrapy.Request(
                    source_url,
                    callback=self.parse_article_content,
                    dont_filter=True,
                    meta=copy.deepcopy(meta)
                )
        # turn page
        if "NEXT" in response.xpath('//div[@class=\"pagedContainer first clearfix\"]//text()').extract():
            next_page = ''.join(response.xpath('//div[@class=\"pagedContainer first clearfix\"]/a[@class=\"next page-numbers\"]/@href').extract()).strip()
            if next_page:
                next_page_url = urlparse.urljoin(response.url, next_page)
            yield scrapy.Request(
                next_page_url,
                callback=self.parse,
                dont_filter=True
            )

    def parse_article_content(self, response):
        # htmls path
        htmls_path = {}
        htmls_path[response.url] = response.body
        # item and json
        item = self.get_new_item()
        json = {}
        # title
        title = ''.join(response.xpath('//h1[@class=\"page-title\"]/text()').extract()).strip()
        json['title'] = title
        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        # author
        authors = {}
        if response.xpath('//p[@class=\"articleInfo\"]'):
            if response.xpath('//p[@class=\"articleInfo\"]/a/text()'):
                author_name = ''.join(response.xpath('//p[@class=\"articleInfo\"]/a/text()').extract()).strip()
                authors['name'] = author_name
            else:
                authors['name'] = None

            if response.xpath('//p[@class=\"articleInfo\"]/a/@href'):
                author_partial_url = ''.join(response.xpath('//p[@class=\"articleInfo\"]/a/@href').extract()).strip()
                author_url = urlparse.urljoin(response.url, author_partial_url)
                authors['url'] = author_url
            else:
                authors['url'] = None
        json['authors'] = authors

        # date
        partial_date = ''.join(response.xpath('//p[@class=\"articleInfo\"]/text()').extract()).strip()
        date = partial_date.split("|")[1]
        if date:
            json['date'] = date

        # image
        caption_images = {}
        image_urls = []
        for image in response.xpath('//article[@class=\"entry-content clearfix\"]/div'):
            if image:
                # image url
                partial_image_url = ''.join(image.xpath('.//@href').extract()).strip()
                if partial_image_url:
                    image_url = urlparse.urljoin(response.url, partial_image_url)
                else:
                    image_url = None
                # image desc
                if image.xpath('./p//text()'):
                    image_desc = ''.join(image.xpath('./p//text()').extract()).strip()
                else:
                    image_desc = None
                # image alt
                if image.xpath('./a/img/@alt'):
                    image_alt = ''.join(image.xpath('./a/img/@alt').extract()).strip()
                else:
                    image_alt = None
                if image_url:
                    caption_images[image_url] = (image_desc, image_alt)
                    image_urls.append(image_url)

        json['caption_images'] = caption_images
        item['image_urls'] = image_urls

        # content
        article = response.xpath(
            '//article[@class=\"entry-content clearfix\"]'
        )
        content_document = fromstring(article.extract()[0].strip())

        # delete title
        if len(content_document.xpath('.//h1[@class=\"page-title\"]')) > 0:
            del_title = content_document.xpath('.//h1[@class=\"page-title\"]')[0]
            del_title.getparent().remove(del_title)

        # delete article info
        if len(content_document.xpath('.//p[@class=\"articleInfo\"]')) > 0:
            del_title = content_document.xpath('.//p[@class=\"articleInfo\"]')[0]
            del_title.getparent().remove(del_title)
        # image replacement

        captions = content_document.xpath('./div')

        if captions:
            for caption in captions:
                if caption.xpath('./a'):
                    keep_img = caption.xpath('./a')[0]
                    caption.addnext(keep_img)
                    caption.getparent().remove(caption)
                else:
                    continue

        # remove related links
        if len(content_document.xpath('./h4')) > 0:
            del_rela_links = content_document.xpath('./h4')[0]
            del_rela_links.getparent().remove(del_rela_links)
        if len(content_document.xpath('./ul')) > 0:
            del_rela_links2 = content_document.xpath('./ul')[0]
            del_rela_links2.getparent().remove(del_rela_links2)

        json["content"] = tostring(content_document, encoding="UTF-8")

        item['json'] = json
        item['htmls_path'] = htmls_path
        item["html"] = response.body

        yield item
