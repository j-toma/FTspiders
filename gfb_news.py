# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring
import copy
from data_fetchers import utils


class GfbNews(Spider):
    name = 'gfb_news'
    source_crawler = "gfb"
    crawl_type = "news"
    version = 0
    allowed_domains = ['www.gfb.org']
    start_urls = [
        "http://www.gfb.org/agnews/default.asp"
    ]
    all_url = set()

    def parse(self, response):
        info_pool = fromstring("".join(response.xpath("//div[@id='Tableholder']").extract()).strip())
        url_path = info_pool.xpath(".//p[contains(@style,'font-size:12px')]")
        for element in url_path:
            # source url
            source_url = urlparse.urljoin(response.url, element.xpath(".//a/@href")[0].strip("..").encode("UTF-8"))

            excerpt = tostring(element.getprevious(), encoding="UTF-8")
            meta = {
                'excerpt': excerpt,
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler=self.source_crawler,
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
        # turning pages:
        if 'Older' in ''.join(response.xpath('//input[@name=\"btnOlder\"]/@value').extract()).strip():
            display_top = str(''.join(response.xpath(
                '//form[@name=\"frmStory\"]//input[@name=\"DisplayRecordIDTop\"]/@value'
            ).extract()).strip())

            display_bottom = str(''.join(response.xpath(
                '//form[@name=\"frmStory\"]//input[@name=\"DisplayRecordIDBottom\"]/@value'
            ).extract()).strip())
            yield scrapy.FormRequest(
                response.url,
                formdata={
                    "DisplayRecordIDTop": display_top,
                    "DisplayRecordIDBottom": display_bottom,
                    "btnOlder": "Older"
                },
                callback=self.parse,
            )

    def parse_article_content(self, response):
        item = self.get_new_item(response)
        json = {}

        # excerpt
        excerpt = response.meta['excerpt']
        json['excerpt'] = excerpt

        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url

        htmls_path = {}
        htmls_path[response.url] = response.body
        item["html"] = response.body
        item['htmls_path'] = htmls_path

        # title
        title = ''.join(response.xpath('//p[@style=\"font-size:17px;color: #990000\"]//text()').extract()).strip()
        if title:
            json['title'] = title

        # caption
        if response.xpath('//div[@id=\"Tableholder\"]//div[@id=\"caption\"]'):
            image_urls = []
            caption_images = {}
            for element in response.xpath('//div[@id=\"Tableholder\"]//div[@id=\"caption\"]'):

                # url
                partial_url = ''.join(element.xpath('./p/img/@src').extract()).strip()

                if partial_url:
                    caption_url = urlparse.urljoin(
                        response.url, partial_url
                    )
                # desc
                description = ''.join(element.xpath('./div//text()').extract()).strip()
                if description:
                    desc = description
                else:
                    desc = None
                # alt/title

                if element.xpath(".//@alt"):
                    image_alt = element.xpath("./p/img/@alt").extract()[0].strip()
                elif element.xpath(".//img/@title"):
                    image_alt = element.xpath("./p/img/@title").extract()[0].strip()
                else:
                    image_alt = None
                if caption_url:
                    caption_images[caption_url] = (desc, image_alt)
                    image_urls.append(caption_url)

            item['image_urls'] = image_urls
            json['caption_images'] = caption_images

        # author and date
        mix = ''.join(response.xpath('//div[@id=\"Tableholder\"]/text()').extract()).strip()
        author = mix.split('\r\n')[0]
        if author:
            json['author'] = author
        date = mix.split('\r\n')[1]
        if date:
            json['date'] = date

        # content
        article = response.xpath('//div[@id=\"Tableholder\"]')
        if article:
            content_document = fromstring(article.extract()[0].strip())
        if not article:
            return

        if len(content_document.xpath('./text')) > 0:
            del_author = content_document.xpath('./text')[0]
            del_author.getparent().remove(del_author)
        if len(content_document.xpath('./p[@style=\"font-size:17px;color: #990000\"]')) > 0:
            del_title = content_document.xpath('./p[@style=\"font-size:17px;color: #990000\"]')[0]
            del_title.getparent().remove(del_title)

        json["content"] = tostring(content_document, encoding="UTF-8")

        item['json'] = json

        yield item
