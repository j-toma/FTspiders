# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from data_fetchers import utils
from lxml.html import fromstring, tostring
import datetime


class WesternFarmPress(Spider):
    name = 'westernfarmpress'
    source_crawler = "wfp"
    crawl_type = "news"
    version = 0
    allowed_domains = ['http://westernfarmpress.com']
    start_urls = ["http://westernfarmpress.com/site-archive"]
    all_urls = set()

    def parse(self, response):
        month_list = response.xpath("//ul[@class=\"views-summary\"]/li/a/@href"
                                    ).extract()
        for month in month_list[:10]:
            month_url = urlparse.urljoin(response.url, month)
            if month_url:
                yield scrapy.Request(
                    month_url,
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_list(self, response):

        partial_urls = response.xpath("//div[@class=\"view-content\"]//div[@class=\"title\"]/a/@href").extract()
        for partial_url in partial_urls:
            article_url = urlparse.urljoin(response.url, partial_url)
            meta = {"article_url": article_url}
            if article_url:
                if not self.check_existance(sourceCrawler='wfp',
                                            sourceURL=article_url,
                                            items_scraped=self.items_scraped) and article_url not in self.all_urls:
                    self.all_urls.add(article_url)
                    yield scrapy.Request(
                        article_url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=meta
                    )

        next_partial = response.xpath(
            "//ul[@class=\"pager\"]//li[@class=\"pager-next last\"]/a/@href").extract()
        if next_partial:
            next_url = urlparse.urljoin(response.url, next_partial[0])
            if next_url:
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_article(self, response):

        item = self.get_new_item(response)
        sourceurl = response.meta["article_url"]
        item["source_url"] = sourceurl
        item['htmls_path'] = {}
        json = {}
        image_urls = []
        caption_images = {}
        if "gallery-content pm-gal-content" in ''.join(response.xpath("//div[@class=\"content clear-block\"]").extract()).strip():
            gallery_content = response.xpath("//div[contains(@class,'content clear-block')]/div[contains(@class,'gallery-content pm-gal-content')]")
            images = gallery_content.xpath(".//li[contains(@class,'pm-gal-slide')]")
            for image in images:
                image_src = urlparse.urljoin(response.url, image.xpath(".//div[contains(@class,'pm-slide-container')]/img/@src").extract()[0].strip())
                if image.xpath(".//div[contains(@class,'pm-slide-container')]/img/@alt"):
                    image_alt = image.xpath(".//div[contains(@class,'pm-slide-container')]/img/@alt").extract()[0].strip()
                elif image.xpath(".//div[contains(@class,'pm-slide-container')]/img/@title"):
                    image_alt = image.xpath(".//div[contains(@class,'pm-slide-container')]/img/@title").extract()[0].strip()
                else:
                    image_alt = "".join(response.xpath("//h1[contains(@class,'page-title')]/text()").extract()).strip()
                image_caption_title = ""
                if image.xpath(".//div[contains(@class,'panel-overlay')]//h3"):
                    image_caption_title = image.xpath(".//div[contains(@class,'panel-overlay')]//h3/text()").extract()[0].strip() + ":"
                image_caption_content = ""
                if image.xpath(".//div[contains(@class,'panel-overlay')]//p"):
                    image_caption_content = "".join(image.xpath(".//div[contains(@class,'panel-overlay')]//p").extract()).strip()
                image_caption = image_caption_title + image_caption_content
                image_urls.append(image_src)
                caption_images[image_src] = (image_caption,image_alt)
        images = response.xpath("//div[contains(@class,'article-image')]")
        for image in images:
            image_src = urlparse.urljoin(response.url, image.xpath(".//img/@src").extract()[0].strip())
            if image.xpath(".//img/@alt"):
                image_alt = image.xpath(".//img/@alt").extract()[0].strip()
            elif image.xpath(".//img/@title"):
                image_alt = image.xpath(".//img/@title").extract()[0].strip()
            else:
                image_alt = "".join(response.xpath("//h1[contains(@class,'page-title')]/text()").extract()).strip()
            image_caption = "".join(image.xpath(".//div[contains(@class,'image-credits')]").extract()).strip()
            caption_images[image_src] = (image_caption, image_alt)
            image_urls.append(image_src)
        item['image_urls'] = image_urls
        json["caption_images"] = caption_images

        title = response.xpath("//h1[contains(@class,'page-title')]")
        if title:
            json['title'] = "".join(title.xpath(".//text()").extract()).strip()

        title_caption = response.xpath("//div[@class=\"deck\"]")
        if title_caption:
            json['title_caption'] = title_caption.xpath(".//text()").extract()[0].strip()

        date = response.xpath("//div[contains(@class,\"byline-date\")]//span[contains(@class,\"publish-date\")]")
        if date:
            json['date'] = date.xpath(".//text()").extract()[0].strip()

        author = response.xpath("//div[@class=\"content-tools\"]//a[@rel=\"author\"]")
        if author and author.xpath(".//text()"):
            json['author'] = author.xpath(".//text()").extract()[0].strip()

        bullet_summary = response.xpath("//div[@class=\"summary\"]/ul/li")
        if bullet_summary:
            json['summary'] = '\n'.join(response.xpath("//div[@class=\"summary\"]/ul/li/text()").extract()).strip()
        paragraph_summary = response.xpath("//div[@class=\"summary\"]/p")
        if paragraph_summary:
            json['summary'] = "".join(paragraph_summary.xpath(".//text()").extract()).strip()

        meta = {'json': json, 'item': item, "sourceurl": sourceurl}
        yield scrapy.Request(
            response.url,
            callback=self.parse_content,
            dont_filter=True,
            meta=meta
        )

    def parse_content(self, response):
        sourceurl = response.meta["sourceurl"]
        json = response.meta["json"]
        item = response.meta["item"]

        content = response.xpath("//div[contains(@class,\"content clear-block\")]").extract()
        if "gatedLogin well" in ''.join(response.xpath("//div[@class=\"content clear-block\"]").extract()).strip():
            content = response.xpath("//div[@class=\"truncated-body\"]").extract()
            if not content:
                if "gallery-content pm-gal-content" in ''.join(response.xpath("//div[@class=\"content clear-block\"]").extract()).strip():
                    content= response.xpath("//div[@class=\"node-body gallery-body\"]").extract()
                    if not content:
                        if "emvideo emvideo-video emvideo-limelight" in ''.join(response.xpath("//div[@class=\"content clear-block\"]").extract()).strip():
                            content = response.xpath("//div[@class=\"node-body video-body\"]").extract()

        content_document=fromstring(content[0].strip())
        del_images = content_document.xpath("//div[contains(@class,'article-image')]")
        for del_image in del_images:
            keep_img = del_image.xpath(".//img")[0]
            del_image.addnext(keep_img)
            del_image.getparent().remove(del_image)

        del_gallery_images = content_document.xpath("//div[contains(@class,'gallery-content pm-gal-content')]")
        for del_gallery_image in del_gallery_images:
            if del_gallery_image.xpath(".//div[contains(@class,'node-body')]"):
                keep_content = del_gallery_image.xpath(".//div[contains(@class,'node-body')]")[0]
                del_gallery_image.addnext(keep_content)
            if del_gallery_image.xpath(".//li[contains(@class,'pm-gal-slide')]"):
                for image in reversed(del_gallery_image.xpath(".//li[contains(@class,'pm-gal-slide')]")):
                    del_gallery_image.addnext(image.xpath(".//div[contains(@class,'pm-slide-container')]/img")[0])
            del_gallery_image.getparent().remove(del_gallery_image)

        del_related = content_document.xpath("//p[text()='More from Western Farm Press']")
        if del_related:
            del_related = del_related[0]
            del_related.getparent().remove(del_related)
        del_related_content = content_document.xpath("//div[@class=\"related-content\"]")
        if del_related_content:
            del_related_content = del_related_content[0]
            del_related_content.getparent().remove(del_related_content)
        del_social_bar = content_document.xpath(".//div[contains(@class,'social-bar')]")
        if del_social_bar:
            del_social_bar = del_social_bar[0]
            del_social_bar.getparent().remove(del_social_bar)
        del_related_media_scroller = content_document.xpath(".//div[@id='related-media-scroller']")
        if del_related_media_scroller:
            del_related_media_scroller = del_related_media_scroller[0]
            del_related_media_scroller.getparent().remove(del_related_media_scroller)
        if "content" in json:
            json["content"] = "".join([json["content"],tostring(content_document, encoding="UTF-8")])
        else:
            json["content"] = tostring(content_document, encoding="UTF-8")

        # item['htmls_path'][sourceurl] = response.body

        htmls_path = response.meta["item"].setdefault("htmls_path",{})
        htmls_path = {
            sourceurl: response.body
        }
        item["htmls_path"] = htmls_path
        have_next = response.xpath("//div[@class=\"pagination-index item-list\"]//li[@class=\"pager-next last\"]/a/@href").extract()
        if have_next:
            page_url = urlparse.urljoin(response.url, have_next[0])
            meta = {'json': json, 'item': item, "sourceurl": page_url}
            yield scrapy.Request(
                page_url,
                callback=self.parse_content,
                dont_filter=True,
                meta=meta
            )

        if not have_next:
            item['json'] = json
            item["html"] = response.body
            item['created_time'] = datetime.datetime.now()

            yield item
