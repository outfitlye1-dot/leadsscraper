import scrapy


class BusinessLeadItem(scrapy.Item):
    company_name = scrapy.Field()
    website = scrapy.Field()
    email = scrapy.Field()
    phone = scrapy.Field()
    linkedin_url = scrapy.Field()
    instagram_url = scrapy.Field()
    facebook_url = scrapy.Field()
    notes = scrapy.Field()
    source = scrapy.Field()
