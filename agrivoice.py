# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
# from data_fetchers.items import DataFetchersItem
from lxml.html import fromstring, tostring


class AgriVoice(Spider):
    name = 'agrivoice'
    source_crawler = 'agrivoice'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://www.fb.org/']
    start_urls = ['http://www.fb.org/newsroom/news_archives/2015/',
                  'http://www.fb.org/newsroom/focusarchives/2015/']
    all_urls = set()

    def parse(self, response):
        years = response.xpath("//*[@id='sidebar']/div[2]/a/@href")
        for year in years:
            year_url = urlparse.urljoin(response.url, year.extract())
            yield scrapy.Request(year_url, callback=self.parse_year, dont_filter=True)

    def parse_year(self, response):
        meta = {}
        articles = response.xpath(".//td[@width=\'25%\']|.//td[@valign=\'top\']")
        for article in articles:
            if article.xpath(".//text()"):
                date = article.xpath(".//text()").extract()[0].replace(u'\xa0', ' ')
            following = article.xpath("./following-sibling::td")
            if following.xpath(".//a/@href"):
                url = urlparse.urljoin(response.url, following.xpath(".//a/@href").extract()[0])
            if following.xpath(".//a/text()"):
                title = following.xpath(".//a/text()").extract()[0]
            if len(date) > 1 and len(url) > 1 and len(title) > 1:
                meta = {'date': date, 'url': url, 'title': title}
                if url:
                    if not self.check_existance(sourceCrawler='agrivoice',
                                                sourceURL=url,
                                                items_scraped=self.items_scraped) and url not in self.all_urls:
                        self.all_urls.add(url)
                        yield scrapy.Request(
                            url,
                            callback=self.parse_article,
                            dont_filter=True,
                            meta=meta)

    def parse_article(self, response):
        item = self.get_new_item(response)
        source_url = response.meta['url']
        item['source_url'] = source_url
        html = response.body
        item['html'] = html
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = []
        item['image_urls'] = []
        item['json']['date'] = response.meta['date'] if 'date' in response.meta else ""
        item['json']['title'] = response.meta['title'] if 'title' in response.meta else ""

        content = response.xpath("//div[@class='article']")
        if not content:
            content = response.xpath("//div[@class='contentleft']")
        if content:
            bulk_content = fromstring(content.extract()[0])
        else:
            return

        # remove date from focus on ag
        if bulk_content.xpath(".//h2"):
            if bulk_content.xpath(".//h2")[0].getprevious():
                date = bulk_content.xpath("//h2")[0].getprevious()
                date.getparent().remove(date)

        title = content.xpath(".//h2")
        if title:
            item['json']['content'] = ''.join(content.xpath(".//h2//text()").extract()).strip()
            del_title = bulk_content.xpath(".//h2")[0]
            del_title.getparent().remove(del_title)

        author = content.xpath(".//strong/em/text()")
        if author:
            item['json']['author'] = author.extract()[0]
            del_author = bulk_content.xpath(".//strong")[0]
            del_author.getparent().remove(del_author)

        # remove images from outside (usually icons)
        if bulk_content.xpath(".//img"):
            for image in bulk_content.xpath(".//img"):
                ancestor_tags = [ancestor.tag for ancestor in image.iterancestors()]
                if 'table' not in ancestor_tags:
                    image.getparent().remove(image)

        tables = bulk_content.xpath(".//div/table|./table")
        sel_tables = content.xpath(".//div/table|./table")
        html_sel = dict(zip(tables, sel_tables))
        imgs = []
        capd_imgs = {}
        if tables:
            for table in tables:
                loc = html_sel[table]
                flag = False
                # audio
                if 'm3u' in loc.extract()[0] or 'm3u' in loc.extract():
                    flag = True
                # video
                if loc.xpath(".//td"):
                    if '<!-- Start of Brightcove Player -->' in loc.xpath(".//td").extract()[0]:
                        flag = True
                # imgs
                if not flag and 'jpg' in loc.extract() or 'jpg' in loc.extract()[0]:
                    html_tds = table.xpath(".//td")
                    tds = loc.xpath(".//td")
                    html_sel_tds = dict(zip(tds, html_tds))
                    for td in tds:
                        el = html_sel_tds[td]
                        if 'jpg' in td.extract() or 'jpg' in td.extract()[0] or 'png' in td.extract():
                            if 'Download' not in td.extract() and 'Download' not in td.extract()[0]:
                                img = td.xpath(".//img/@src")
                                if img:
                                    image_url = urlparse.urljoin(response.url, img.extract()[0])
                                    imgs.append(image_url)
                                    if td.xpath(".//img/@alt"):
                                        image_alt = td.xpath(".//img/@alt").extract()[0]
                                    elif td.xpath(".//img/@title"):
                                        image_alt = td.xpath(".//img/@title").extract()[0]
                                    else:
                                        image_alt = None
                                    image_cap = td.xpath(".//span/text()|.//em/text()|.//strong/text()").extract()[0] if td.xpath(".//span/text()|.//em/text()|.//strong/text()") else None
                                    if image_cap:
                                        if image_cap.endswith("(Click image for high resolution version.)"):
                                            image_cap = image_cap[:-42]
                                        if image_cap == 'Click on the image for a high resolution version.':
                                            image_cap = None
                                    capd_imgs[image_url] = (image_cap, image_alt)
                                    keep_img = el.xpath(".//img")[0]
                                    for ancestor in el.iterancestors():
                                        if ancestor.tag == 'table':
                                            ancestor.addnext(keep_img)
                    flag = True
                # contacts
                if loc.xpath(".//td/strong/text()") or loc.xpath(".//td/b/text()"):
                    if 'Contacts:' in loc.xpath(".//td/strong/text()|.//td/b/text()").extract()[0]:
                        flag = True
                if loc.xpath("//table[@id=\'link_images\']"):
                    flag = True
                # remove table
                if flag:
                    table.drop_tree()
        # save images
        if imgs is not None:
            item['image_urls'] = imgs
            item['json']['caption_images'] = capd_imgs

        # OUTSIDE of tables
        # remove '-30-' from news
        if bulk_content.xpath(".//p[text()='-30-']"):
            page_number = bulk_content.xpath(".//p[text()='-30-']")[0]
            page_number.getparent().remove(page_number)
        # remove videos
        if bulk_content.xpath(".//object"):
            for brightcove in bulk_content.xpath(".//object"):
                brightcove.getparent().remove(brightcove)
        # remove author information
        if bulk_content.xpath(".//hr"):
            line = bulk_content.xpath(".//hr")[0]
            for sibling in line.itersiblings():
                sibling.getparent().remove(sibling)
            line.getparent().remove(line)

        item['json']['content'] = tostring(bulk_content,encoding='utf-8')

        yield item
