# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from data_fetchers import utils


class Growingmagazine(Spider):
    name = 'growingmagazine'
    source_crawler = "growingmagazine"
    crawl_type = "news"
    version = 0
    allowed_domains = ['www.growingmagazine.com']
    start_urls = [
        "http://www.growingmagazine.com/category/education/latestnews/"
    ]
    all_url = set()

    def parse(self, response):
        article = response.xpath('//div[@class=\"row archive-posts vw-isotope post-box-list\"]//div[@class=\"col-sm-6 post-box-wrapper\"]')
        for element in article:
            # source url
            source_url = ''.join(element.xpath('./article//h3[@class=\"title\"]/a/@href').extract()).strip()
            # article title
            title = ''.join(element.xpath('./article//h3[@class=\"title\"]/a/text()').extract()).strip()

            meta = {
                'title': title,
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler='growingmagazine',
                                        sourceURL=source_url,
                                        items_scraped=self.items_scraped)\
                    and source_url not in self.all_url:
                self.all_url.add(source_url)
                yield scrapy.Request(
                    source_url,
                    callback=self.parse_article_content,
                    dont_filter=True,
                    meta=meta
                )

        # turning pages:
        if response.xpath('//div[@id=\"pagination\"]//a[@class=\"next page-numbers\"]'):
            next_page = ''.join(response.xpath('//div[@id=\"pagination\"]//a[@class=\"next page-numbers\"]//@href').extract()).strip()
            next_page_url = urlparse.urljoin(response.url, next_page)

            yield scrapy.Request(
                next_page_url,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_article_content(self, response):
        # get item and json
        item = self.get_new_item()
        json = {}

        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        # html path
        htmls_path = {}
        htmls_path[response.url] = response.body
        item["html"] = response.body
        item['htmls_path'] = htmls_path

        # title
        title = response.meta['title']
        if title:
            json['title'] = title

        # author
        authors = {}
        author_name = ''.join(response.xpath('//div[@id=\"page-content\"]/article/div[@class=\"post-meta header-font\"]/a//text()').extract()[0]).strip()
        if author_name:
            authors['name'] = author_name
        json['authors'] = authors

        # date
        date = ''.join(response.xpath('//div[@id=\"page-content\"]/article/div[@class=\"post-meta header-font\"]/a//text()').extract()[1]).strip()
        if date:
            json['date'] = date

        # caption
        image_urls = []
        caption_images = {}
        images = response.xpath('//div[@class=\"post-content clearfix\"]')
        if images:
            for image in images:
                # desc
                description = ''.join(image.xpath('.//img/@alt').extract()).strip()
                if description:
                    desc = description
                else:
                    desc = None

                # url
                partial_url = ''.join(image.xpath('.//img/@src').extract()).strip()
                if partial_url:
                    caption_url = urlparse.urljoin(
                        response.url, partial_url
                    )
                else:
                    caption_url = None

                    # alt/title
                if image.xpath("./a//@alt"):
                        image_alt = image.xpath("./a//@alt").extract()
                elif image.xpath("./a//@title"):
                    image_alt = image.xpath("./a//@title").extract()
                else:
                    image_alt = None
                if caption_url:
                    caption_images[caption_url] = (desc, image_alt)
                    image_urls.append(caption_url)
            item['image_urls'] = image_urls
            json['caption_images'] = caption_images
        else:
            pass

        # content

        article = response.xpath(
            '//div[@class=\"post-content clearfix\"]'
        )
        content = ''.join(article.xpath('.//p/text()').extract()).strip()

        json["content"] = content
        item['json'] = json
        yield item
