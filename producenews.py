# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers.items import DataFetchersItem
from scrapy.selector import Selector
from scrapy.contrib.spiders import XMLFeedSpider
from data_fetchers import utils
from lxml.html import fromstring, tostring, Element
from data_fetchers.spider import Spider


class ProduceNewsPlus(Spider):
    name = "producenewsplus"
    source_crawler = 'producenews'
    crawl_type = 'news'
    version = 1
    allowed_domains = []
    start_urls = [
        'http://www.theproducenews.com/more-markets-and-trends',
        'http://www.theproducenews.com/more-company-profiles',
        'http://www.theproducenews.com/more-people-articles',
        'http://www.theproducenews.com/more-recent-headlines',
        'http://www.theproducenews.com/more-sightings',
    ]
    all_urls = set()

    def parse_item(self, response):
        item = self.get_new_item(response)
        html = utils.decode(response.body, response.encoding)
        article = response.xpath("//div[contains(@class,'item-page')]")
        caption_images = {}
        caption_imgs = article.xpath(".//p/span[contains(@class,'wf_caption')]")
        imgs = article.xpath(".//p/img")
        for caption_img in caption_imgs:
            if caption_img.xpath(".//img/@alt"):
                image_alt = caption_img.xpath(".//img/@alt").extract()[0].strip()
            elif caption_img.xpath(".//img/@title"):
                image_alt = caption_img.xpath(".//img/@title").extract()[0].strip()
            else:
                image_alt = None
            caption_images[urlparse.urljoin(response.url, caption_img.xpath(".//img/@src").extract()[0].strip())] = ("".join(caption_img.xpath(".//span").extract()),image_alt)
        for img in imgs:
            if img.xpath(".//@alt"):
                image_alt = img.xpath(".//@alt").extract()[0].strip()
            elif img.xpath(".//@title"):
                image_alt = img.xpath(".//@title").extract()[0].strip()
            else:
                image_alt = None
            caption_images[urlparse.urljoin(response.url, img.xpath(".//@src").extract()[0])] = (None,image_alt)
        slid_imgs = []
        for main_images_wrapper in response.xpath("//div[contains(@id,'main_images_wrapper')]"):
            desc = []
            image_info = []
            for main_des_container in main_images_wrapper.xpath(".//div[contains(@id,'main_des_container')]/div[contains(@class,'des_div')]/p"):
                desc.append(main_des_container.xpath(".//text()").extract()[0].strip())
            for img_tag in main_images_wrapper.xpath(".//div[contains(@id,'main_thumbs_arrow_wrapper')]/div[contains(@id,'main_thumb_container')]//img[contains(@class,'ig_thumb')]"):
                if img_tag.xpath(".//@src"):
                    path = urlparse.urljoin(response.url,img_tag.xpath(".//@src").extract()[0].strip().replace("120-90-80-c","600-450-80"))
                    slid_imgs.append(path)
                else:
                    path = ""
                alt = img_tag.xpath(".//@alt").extract()[0].strip() if img_tag.xpath(".//@alt") else None
                image_info.append((path,alt))
            for i in xrange(len(desc)):
                caption_images[image_info[i][0]] = (desc[i],image_info[i][1])
        item['image_urls'] = [u for u in caption_images.keys()]
        item["json"]["caption_images"] = caption_images

        createdby = response.xpath("//dd[@class='createdby']//text()").extract()[0]
        createdBySplit = createdby.split('|')
        if len(createdBySplit) >= 2:
            item['json']['author'] = createdBySplit[0].strip()[3:]
            item['json']['date'] = createdBySplit[1].strip()
        else:
            item['json']['date'] = createdby.strip()

        item['json']['title'] = article.xpath(".//h2/text()").extract()[0].strip()
        item['json']['item_url'] = response.url

        content_document=fromstring(article.extract()[0].strip())
        del_title = content_document.xpath(".//h2")[0]
        del_title.getparent().remove(del_title)
        del_author_date = content_document.xpath(".//dl[contains(@class,'article-info')]")[0]
        del_author_date.getparent().remove(del_author_date)
        if content_document.xpath(".//div[contains(@id,'main_images_wrapper')]"):
            del_main_images_wrapper = content_document.xpath(".//div[contains(@id,'main_images_wrapper')]")[0]
            for image_url in slid_imgs:
                img_doc = Element("img",**{"src":image_url})
                del_main_images_wrapper.addprevious(img_doc)
            del_main_images_wrapper.getparent().remove(del_main_images_wrapper)
        del_igallery_clear_div = content_document.xpath(".//div[contains(@class,'igallery_clear')]")[0]
        del_igallery_clear_div.getparent().remove(del_igallery_clear_div)
        captions = content_document.xpath(".//p/span[contains(@class,'wf_caption')]")
        if captions:
            for caption in captions:
                keep_img = caption.xpath(".//img")[0]
                caption.addnext(keep_img)
                caption.getparent().remove(caption)
        item["json"]["content"] = tostring(
            content_document,
            encoding="UTF-8"
        )

        sourceurl = response.meta['source_url']
        item['json']['category'] = response.meta['category']
        item['html'] = html
        htmls_path = {
            sourceurl:html
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = sourceurl
        return item

    def parse(self, response):
        self.log('========= list is list page! %s' % response.url)
        category = response.xpath("//div[@class='article_cat']/p/text()").extract()
        urls = response.xpath("//div[@class='peolpleContainer']//a[@class='qmininews-thumb-link']//@href").extract()
        for url in urls:
            fullurl = urlparse.urljoin(response.url, url)
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=fullurl,
                                        items_scraped=self.items_scraped) and \
                    fullurl not in self.all_urls:
                self.all_urls.add(fullurl)
                yield scrapy.Request(fullurl, callback=self.parse_item, dont_filter=True, meta={"source_url": fullurl, "category": category})
