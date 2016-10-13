from collections import OrderedDict
from html.parser import HTMLParser
from urllib.request import Request, urlopen
import urllib.parse
import math
import json
import sys
import re

class SimpleRequest(Request):
    """Небольшое упрощение запросов"""
    def __init__(self, url, data={}, headers={}, 
        origin_req_host=None, unverifiable=False, method=None):
        if data:
            data = urllib.parse.urlencode(data)
            data = data.encode('ascii')
        else:
            data = None

        super(SimpleRequest, self).__init__(url, data, headers,
         origin_req_host, unverifiable, method)

        self.response = urlopen(self)
        self.htmlParser = HTMLParser()

    def getResponsePage(self, decode = '1251',unescape = False):
        if unescape:
            return self.htmlParser.unescape(self.response.read().decode(decode))
        else:
            return self.response.read().decode(decode)

    def getResponseCookie(self,cookie):
        listCookie = []
        listHeaders = list(self.response.info().values())
        patternCookie = '{}=\w+;'.format(cookie)
        for header in listHeaders:
            findPattern = re.search(patternCookie,header)
            if findPattern:
                listCookie.append(findPattern.group())
        return listCookie[-1]


class VkRequest():
    """авторизация в вк и запросы к страницам"""
    def __init__(self, login, password):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'}
        openVkAuthorizationPage = SimpleRequest('https://vk.com/',headers=headers)

        text = openVkAuthorizationPage.getResponsePage()
        pattern_ip_h = '"ip_h" value="\w+"'
        pattern_lg_h = '"lg_h" value="\w+"'
        ip_h = re.search(pattern_ip_h, text).group().split('"')[-2]
        lg_h = re.search(pattern_lg_h, text).group().split('"')[-2]

        cookies = "{} {}".format(openVkAuthorizationPage.getResponseCookie("remixlhk"),
                                openVkAuthorizationPage.getResponseCookie("remixlang"))
        headers['Cookie'] = cookies
        data = OrderedDict([('act','login'),('role','al_frame'),('expire',''),('captcha_sid',''),('captcha_key',''),
        ('_origin','https://vk.com'),('ip_h',ip_h),('lg_h',lg_h),('email',login),('pass',password)])

        getAuthorizationKey = SimpleRequest('https://login.vk.com/?act=login', headers=headers, data = data)
        self.remixsid = getAuthorizationKey.getResponseCookie("remixsid")
        self.remixlang = getAuthorizationKey.getResponseCookie("remixlang")
        

    def getVkPage(self, page, cookie = None, headers = None, data = None):
        if not cookie:
            cookie = ' '.join([self.remixsid,self.remixlang])
        if not headers:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0',
                        'Cookie':cookie}
        return SimpleRequest(page, headers = headers, data = data).getResponsePage()


    def correctURL(self,adrPage):
        return "https://vk.com/audios" + re.findall('\d+', adrPage)[-1]

    def _getVkPlayList(self,page):
        namePlayList = None
        albumId = None

        strWithNamePlayList = "<div class=\"audio_album_title\" \""
        findStart,findEnd = '">','</div></span>'

        patternAlbumId = "album_id=\d+"

        for line in page.splitlines():
            if strWithNamePlayList in line:
                start = line.find(findStart) + 2
                end = line.find(findEnd)
                namePlayList = line[start:end]
        try:
            albumId = re.findall(patternAlbumId, page)[-1]
        except IndexError:
            return {None:None}

        return {int(albumId.split("=")[-1]):namePlayList}

    def getVkPlayLists(self,adrPage):
        page = self.getVkPage(self.correctURL(adrPage))
        page = page.split('<span>Рекомендации</span>')[-1]
        page = page.split('ui_rmenu_audio_album_')[1:]

        listNamePlayList = []
        listAlbumId = []

        playlists = {0:0}
        for part in page:
            playlists.update(self._getVkPlayList(part))

        return playlists

    def getIds(self,adrPage):
        dictPlaylist = self.getVkPlayLists(adrPage)
        link = "https://vk.com/al_audio.php"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0',
                    'referer' : self.correctURL(adrPage), 'Cookie' : ' '.join([self.remixsid,self.remixlang])}
        data = {'act':"load_silent",'al':1,'album_id':-2,'band':'false',
                'owner_id':re.findall('\d+', adrPage)[-1]}
        jsonOfSongs = self.getVkPage(link,headers=headers,data=data).split('<!json>')[-1]
        listOfSongs = json.loads(jsonOfSongs)["list"]

        ids = []
        for song in listOfSongs:
            dictionary = {}
            dictionary['id_song'] = '{}_{}'.format(song[1],song[0])
            dictionary['playlist'] = dictPlaylist[song[6]]
            dictionary['nameSong']  = song[3]
            dictionary['author'] = song[4]
            dictionary['link'] = None
            ids.append(dictionary)

        return ids

    def getLinks(self, adrPage, IDs, first = 0, end = 10):
        link = "https://vk.com/al_audio.php"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0',
                    'referer' : self.correctURL(adrPage), 'Cookie' : ' '.join([self.remixsid,self.remixlang])}
        ids = ""
        # print("line 124. first: " + str(first) + "end: " + str(end))#here
        # print("line 125. IDs[first:end]: "+str(IDs[first:end]))#here
        for ID in IDs[first:end]:
            ids += ID['id_song'] + ","
        # print('line 128. ids' + ids)#here
        data = {'act':'reload_audio','al':1,'ids':ids[:-1]}
        jsonOfSongs = self.getVkPage(link,headers=headers,data=data)
        # print("line 131. jsonOfSongs: "+str(jsonOfSongs))#here
        links = json.loads(jsonOfSongs.split("<!json>")[-1].split("<!>")[0])

        i = first
        for link in links:
            IDs[i]['link'] = link[2]
            i+=1

        return IDs

    def getChunks(self,ids,sizeChunk = 10):
        i = 0
        j = 0
        chunkIds = []
        for ID in ids:
            if not i:
                chunkIds.append([])

            chunkIds[j].append(ID)

            i += 1
            if i == sizeChunk:
                i = 0
                j += 1

        return chunkIds

    def getParts(self,ids,sizePart):
        sizeChunk = math.ceil(len(ids)/sizePart)
        return self.getChunks(ids,sizeChunk)


if __name__ == '__main__':
    login = str(sys.argv[1])
    password = str(sys.argv[2])
    vkRequest = VkRequest(login, password)
    # print(vkRequest.remixsid)
    # pageAudio = vkRequest.getVkPage('https://vk.com/audios49826188')
    # print(pageAudio)
    # pageAudio = vkRequest.getVkPlayLists('https://vk.com/audios184571890?friend=49826188')
    # print(pageAudio)
    playlists = vkRequest.getVkPlayLists('https://vk.com/audios49826188')
    ids = vkRequest.getIds('https://vk.com/audios49826188')

    parts = vkRequest.getParts(ids,3)
    i = 0
    for part in parts:
        print('-----------------------------------------------------------------')
        print(part)
        i += 1
        print(i)

    # chunkIds = vkRequest.getChunks(ids)


    # for chunk in chunkIds:
    #     print(chunk)
    #     print('------------------------------------')
    # print(ids)

    # j = 0
    # for chunk in chunkIds:
    #     print(j)
    #     print('-------------------------------------------------------')
    #     print(vkRequest.getLinks('https://vk.com/audios49826188',chunk))
    #     j += 1
