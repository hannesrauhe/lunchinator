import os, sys
import time
import datetime

import twitter
import pprint

if __name__ == '__main__':
    #codebear:
    api = twitter.Api(consumer_key='rHL1p36BdsTqXbensAMCA',
                     consumer_secret='XEj1YABZ393xF5gqTLTn3fqlmkNwqxyPtEgwilv7ww',
                     access_token_key='14466014-DnoKbwEZIb9x1aOphCOCvihP4Td1ijZQ9375m8Z6C',
                     access_token_secret='5feInXBv64jcXgc0xQTSQa39FC8SLdF9tSy3svP0',
                     debugHTTP=False)

    #print api.VerifyCredentials()

    since_id = None
    # try:
    #     print '-+'*10, 'polling Public Timeline'
    #     for status in api.GetPublicTimeline(since_id=since_id):
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Friends Timeline'
    #     for status in api.GetFriendsTimeline(retweets=False):
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Followers'
    #     for status in api.GetFollowers():
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Home Timeline'
    #     for status in api.GetFriendsTimeline(retweets=True):
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Blocked Users'
    #     for status in api.GetBlocks('bear'):
    #         item = status.AsDict()
    #         print item['id'], item['screen_name']
    # finally:
    #     print '*'*50
    try:
        print '-+'*10, 'User Timeline'
        for status in api.GetUserTimeline(screen_name='@HistoricalPics'):
            item = status.AsDict()
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(item)
            print status.media[0]["media_url"]
            urls = [url for url in item['text'].split(" ") if url.startswith("http")]
            print urls
            break
    finally:
        print '*'*50
     
    # try:
    #     print '-+'*10, 'Favorites'
    #     for status in api.GetFavorites():
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # try:
    #     print '-+'*10, 'Mentions'
    #     for status in api.GetMentions():
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Retweets by User'
    #     for status in api.GetUserRetweets():
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Trends Daily'
    #     for hourList in api.GetTrendsDaily():
    #         for trend in hourList:
    #             print 'Timestamp: %s Name: %s Query: %s' % (trend.timestamp, trend.name, trend.query)
    #         print '-------'
    # finally:
    #     print '*'*50
    
    # try:
    #     print '-+'*10, 'Lists'
    #     for status in api.GetLists('manta'):
    #         item = status.AsDict()
    #         print item
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Lists List'
    #     for item in api.GetListsList('bear'):
    #         print item.AsDict()
    # finally:
    #     print '*'*50
    #
    # try:
    #     print 'trying list_id alone', len(api.GetListTimeline(list_id=95200241, slug=None))
    #     print 'trying slug + owner_id', len(api.GetListTimeline(list_id=None, slug='xmpp', owner_id=16133)) 
    #     # print 'trying list_id alone (should error out)', len(api.GetListTimeline(list_id=95200241, slug=None))
    #     # print 'trying slug alone (should error out)', len(api.GetListTimeline(list_id=None, slug='xmpp'))
    # finally:
    #     print '*'*50
    #
#     try:
#         print '-+'*10, 'List Members'
#         for user in api.GetListMembers(list_id=16133, slug='xmpp', owner_id=16133):
#             item = user.AsDict()
#             print item
#     finally:
#         print '*'*50
    
    # try:
    #     print '-+'*10, 'Post Test'
    #     api.PostUpdate('Testing oAuth from command line %s' % time.time())
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Post Test - unicode'
    #     s = '\xE3\x81\x82' * 10
    #     api.PostUpdate('%s %s' % (s, time.time()))
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'Post Test - unicode'
    #     s = '\u1490'
    #     api.PostUpdate('%s %s' % (s, time.time()))
    # finally:
    #     print '*'*50
    # try:
    #     print '-+'*10, 'Post Test - unicode'
    #     # make sure input encoding param is set
    #     s = u'\u3042' * 10
    #     api.PostUpdate(u'%s %s' % (s, time.time()))
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'destroy friendship link'
    #     print api.DestroyFriendship("coda").AsDict()
    # finally:
    #     print '*'*50
    # 
    # try:
    #     print '-+'*10, 'create friendship link'
    #     print api.CreateFriendship("coda").AsDict()
    # finally:
    #     print '*'*50



