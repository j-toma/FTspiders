# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from lxml.html import fromstring, tostring
from lxml.cssselect import CSSSelector

from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from data_fetchers.spider import Spider


class PackerPlusSpider(Spider):
    name = "packerplus"
    source_crawler = "thepacker"
    crawl_type = "news"
    version = 1
    allowed_domains = []
    start_urls = [
        'http://www.thepacker.com/packer-rss-index',
    ]
    all_urls = set()

    def parse(self,response):
        url=response.url
        self.log("this is the Packer RSS Index! %s" % url)
        rss_news=response.xpath(CSSSelector("div.field-item a").path)
        for rss_item_news in rss_news:
            rss_item_news_url=urlparse.urljoin(url, rss_item_news.xpath(".//@href").extract()[0].strip())
            rss_item_news_channel=rss_item_news.xpath(".//text()").extract()[0].strip()
            yield scrapy.Request(rss_item_news_url, callback=self.parse_list, dont_filter=True, meta={'channel': rss_item_news_channel})

    def parse_list(self,response):
        url=response.url
        self.log('this is a rss! %s' % url)
        items=response.xpath("//item")
        for item in items:
            if item.xpath(".//link/text()"):
                meta={}
                item_url=urlparse.urljoin(url, item.xpath(".//link/text()").extract()[0].strip())
                meta["source_url"]=item_url
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=item_url,
                                            items_scraped=self.items_scraped) and \
                        item_url not in self.all_urls:
                    self.all_urls.add(item_url)
                    if item.xpath(".//title/text()"):
                        meta["title"]=item.xpath(".//title/text()").extract()[0].strip()
                    if item.xpath(".//description/text()"):
                        meta["description"]=item.xpath(".//description/text()").extract()[0].strip()
                    if item.xpath(".//pubDate/text()"):
                        meta["pubDate"]=item.xpath(".//pubDate/text()").extract()[0].strip()
                    if "channel" in response.meta:
                        meta["channel"]=response.meta["channel"]
                    yield scrapy.Request(item_url, callback=self.parse_item, dont_filter=True, meta=meta)
            else:
                self.log("no url be find! %s" % url)

    def parse_item(self,response):
        url=response.url
        self.log("this is an item page! %s" % url)
        article_section_div=response.xpath(CSSSelector("div.article-section").path)
        if article_section_div and article_section_div.xpath(".//a/text()").extract()[0].strip()=="News":
            html = utils.decode(response.body)
            item = self.get_new_item(response)
            item["thumb_urls"] = []
            json = item["json"]
            tags = []
            for item_tag in response.xpath(CSSSelector("div.field-name-field-topics-the-packer a").path):
                tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(), urlparse.urljoin(url,item_tag.xpath(".//@href").extract()[0].strip()))
                tags.append(tagTuple)
            json['tags'] = tags
            if response.xpath("//h1[contains(@itemprop,'headline')]"):
                json["title"] = response.xpath("//h1[contains(@itemprop,'headline')]/text()").extract()[0].strip()
            else:
                if "title" in response.meta:
                    json["title"]=response.meta["title"]
            json["item_url"]=url
            if "description" in response.meta:
                json["description"]=response.meta["description"]
            if "pubDate" in response.meta:
                json["pubDate"]=response.meta["pubDate"]
            if "channel" in response.meta:
                json["channel"]=response.meta["channel"]
            sourceurl = response.meta["source_url"]

            about_author_div=response.xpath(CSSSelector("div.article-author").path)
            if about_author_div:
                author={}
                if about_author_div.xpath(".//div[@class='author-image']/img/@src"):
                    author["author_img"]=urlparse.urljoin(url,about_author_div.xpath(".//div[@class='author-image']/img/@src").extract()[0].strip())
                if about_author_div.xpath(".//p[@class='author-name']/strong[@itemprop='name']/text()"):
                    author["author_name"]=about_author_div.xpath(".//p[@class='author-name']/strong[@itemprop='name']/text()").extract()[0].strip()
                if about_author_div.xpath(".//p[@class='author-name']/span[@itemprop='jobTitle']/text()"):
                    author["author_jobtitle"]=about_author_div.xpath(".//p[@class='author-name']/span[@itemprop='jobTitle']/text()").extract()[0].strip()
                if about_author_div.xpath(".//div[@class='author-bio']/text()"):
                    author["author_biography"]=about_author_div.xpath(".//div[@class='author-bio']/text()").extract()[0].strip()
                json["author"]=author

            article = response.xpath("//section[contains(@class,'article-content')]")
            figures = article.xpath(".//figure[contains(@class,'article-featured-image')]")
            caption_images = {}
            for figure in figures:
                image_url = urlparse.urljoin(
                    response.url,
                    figure.xpath(".//div[contains(@class,'module-wrapper')]/img/@src").extract()[0].strip()
                )
                if figure.xpath(".//div[contains(@class,'module-wrapper')]/img/@alt"):
                    image_alt = figure.xpath(".//div[contains(@class,'module-wrapper')]/img/@alt").extract()[0].strip()
                elif figure.xpath(".//div[contains(@class,'module-wrapper')]/img/@title"):
                    image_alt = figure.xpath(".//div[contains(@class,'module-wrapper')]/img/@title").extract()[0].strip()
                else:
                    image_alt = None
                image_desc = figure.xpath(".//div[contains(@class,'module-wrapper')]/figcaption[contains(@class,'photo-caption')]")
                caption_images[image_url] = (image_desc.extract()[0].strip() if image_desc else None,image_alt)
            figure_items = article.xpath(".//figure[contains(@class,'item')]")
            for figure_item in figure_items:
                image_url = urlparse.urljoin(
                    response.url,
                    figure_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img/@src").extract()[0].strip()
                )
                if figure_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img/@alt"):
                    image_alt = figure_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img/@alt").extract()[0].strip()
                elif figure_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img/@title"):
                    image_alt = figure_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img/@title").extract()[0].strip()
                else:
                    image_alt = None
                image_desc = figure_item.xpath(".//descendant::div[contains(@class,'credits-caption')]/figcaption[contains(@class,'photo-caption')]")
                caption_images[image_url] = (image_desc.extract()[0].strip() if image_desc else None,image_alt)
            media_items = article.xpath(".//img[@class='media-image']")
            for media_item in media_items:
                image_url = media_item.xpath("./@src").extract()[0]
                if len(media_item.xpath("../text()")) > 0:
                    image_desc = media_item.xpath("../text()").extract()[0].strip()
                else:
                    image_desc = None
                image_alt = None
                caption_images[image_url] = (image_desc, image_alt)

            item['image_urls'] = [u for u in caption_images.keys()]
            json["caption_images"] = caption_images

            content_document = fromstring(article.extract()[0].strip())
            slideshows = content_document.xpath(".//div[@id='vance-slideshow']")
            for slideshow in slideshows:
                for slideshow_item in slideshow.xpath(".//figure[contains(@class,'item')]"):
                    keep_img = slideshow_item.xpath(".//descendant::div[contains(@class,'slide-image')]/img")[0]
                    slideshow.addnext(keep_img)
                slideshow.getparent().remove(slideshow)
            figure_docs = content_document.xpath(".//figure[contains(@class,'article-featured-image')]")
            for figure_doc in figure_docs:
                keep_img = figure_doc.xpath(".//div[contains(@class,'module-wrapper')]/img")[0]
                figure_doc.addnext(keep_img)
                figure_doc.getparent().remove(figure_doc)
            json["content"] = tostring(
                content_document,
                encoding="UTF-8"
            )

            item["json"] = json
            item["html"] = html
            htmls_path = {
                sourceurl:html
            }
            item["htmls_path"] = htmls_path
            item["source_url"]=sourceurl
            yield item
        else:
            self.log('the item is invalid news! %s' % url)
