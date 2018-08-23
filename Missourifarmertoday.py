# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
import copy
from data_fetchers import utils
import datetime


class MissouriFarmerToday(Spider):
    name = 'missourifarmertoday_news'
    source_crawler = "missourifarmertoday"
    crawl_type = "news"
    item_parser="parse_article_content"
    version = 0
    allowed_domains = ['www.missourifarmertoday.com']
    start_urls = [
        "http://www.missourifarmertoday.com/search/?sForm=false&sHeading=News&s=start_time&sd=desc&c=news%2A&nk=%23ap&f=html&l=25&o=0&skin=%2F&app%5B0%5D=editorial"
    ]
    all_url = set()

    def parse(self, response):
        article = response.xpath('//div[@class=\"index-list-container\"]/div[@class=\"index-list-item\"]')
        for element in article:
            # source url
            partial_source_url = ''.join(element.xpath('./h1/a/@href').extract()).strip()
            if partial_source_url:
                source_url = urlparse.urljoin(
                    response.url, partial_source_url
                )
            # article title
            title = ''.join(element.xpath('./h1/a/text()').extract()).strip()
            # excerpt
            excerpt = ''.join(element.xpath('./p[@class=\"excerpt\"]//text()').extract()).strip()
            # thumbnail
            thumbs = element.xpath('./div[@class=\"left small\"]//@src')
            thumb_urls = []
            for thumb in thumbs:
                if thumb:
                    thumb_2 = ''.join(thumb.extract()).strip()
                    thumb = urlparse.urljoin(response.url, thumb_2.strip())
                    thumb_urls.append(thumb)

            meta = {
                'title': title,
                'source_url': source_url,
                'excerpt': excerpt,
                'thumb_urls': thumb_urls
            }
            if not self.check_existance(sourceCrawler='missourifarmertoday',
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
        if 'href' in ''.join(response.xpath('//li[@class=\"next\"]').extract()).strip():
            partial_next_page = ''.join(response.xpath('//li[@class=\"next\"]/a/@href').extract()).strip()
            if partial_next_page:
                next_page = urlparse.urljoin(response.url, partial_next_page)

            yield scrapy.Request(
                next_page,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_article_content(self, response):
        # get item and json
        item = self.get_new_item(response)
        json = item["json"]
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
        # excerpt
        excerpt = response.meta['excerpt']
        if excerpt:
            json['excerpt'] = excerpt
        # thumbnail urls
        thumb_urls = response.meta['excerpt']
        if thumb_urls:
            json['thumb_urls'] = thumb_urls
        # category
        category = ''.join(response.xpath('//span[@class=\"label\"]//text()').extract()).strip()
        if category:
            json['category'] = category

        # caption
        if response.xpath('//div[@id=\"blox-gallery\"]'):
            image_urls = []
            caption_images = {}
            for element in response.xpath('//div[@id=\"blox-gallery"]//img'):

                # url
                partial_url = ''.join(element.xpath('.//@src').extract()).strip()

                if partial_url:
                    caption_url = urlparse.urljoin(
                        response.url, partial_url
                    )

                # desc
                if element.xpath('../div[@id=\"blox-gallery-caption\"]//text()'):
                    description = ''.join(element.xpath('.//div[@id=\"blox-gallery-caption\"]//text()').extract()).strip()
                    if description:
                        desc = description
                else:
                    desc = None

                # alt/title
                if element.xpath(".//@alt"):
                    image_alt = element.xpath(".//@alt").extract()[0].strip()
                elif element.xpath(".//@title"):
                    image_alt = element.xpath(".//@title").extract()[0].strip()
                else:
                    image_alt = title
                if caption_url:
                    caption_images[caption_url] = (desc, image_alt)
                    image_urls.append(caption_url)
            item['image_urls'] = image_urls
            json['caption_images'] = caption_images

        else:
            pass

        # author
        authors = {}
        if response.xpath('//span[@class=\"byline\"]'):
            if response.xpath('//span[@class=\"byline\"]//text()'):
                author_name = ''.join(response.xpath('//span[@class=\"byline\"]//text()').extract()).strip()
                authors['name'] = author_name
            else:
                authors['name'] = None

            if response.xpath('//span[@class=\"byline\"]//@href'):
                author_partial_url = ''.join(response.xpath('//span[@class=\"byline\"]//@href').extract()).strip()
                author_url = urlparse.urljoin(response.url, author_partial_url)
                authors['url'] = author_url
            else:
                authors['url'] = None
        json['authors'] = authors

        # date
        partial_date = ''.join(response.xpath('//div[@class=\"date left\"]/span/text()').extract()).strip()
        if 'hour' in partial_date:
            date_number = int(partial_date.split('hour')[0])
            now = datetime.datetime.now()
            hours = datetime.timedelta(hours=int(date_number))
            date = (now - hours).strftime('%m-%d-%Y %H:%M')
            json['date'] = date
        else:
            date = partial_date
            json['date'] = date
        # content
        content = ''.join(response.xpath('//div[@id=\"article_body\"]/div[@id=\"article_main\"]//p//text()').extract()).strip()
        if content:
            json['content'] = content
        item['json'] = json
        yield item
