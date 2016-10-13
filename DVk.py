from urllib.request import Request, urlopen
from html.parser import HTMLParser
from Progress import printProgress
from multiprocessing import Process, Manager, freeze_support
import SimpleRequest
import time
import pickle
import argparse
import urllib
import os

htmlParser = HTMLParser()

def creatNameFile(author,nameSong):
    nameSong = htmlParser.unescape(author + ' - ' + nameSong)
    if len(nameSong)>200:
        nameSong = nameSong[:200]
    nameSong = chr(8260).join(nameSong.split('/'))
    specialSymbols = ['<', '>', ':' ,'"','\\','|','?','*']
    for special in specialSymbols:
        nameSong = ' '.join(nameSong.split(special))
    return nameSong + '.mp3'

def dowload(ID,path):
    nameSong = creatNameFile(ID['author'],ID['nameSong'])

    try:
        openLink = urlopen(Request(ID['link'], headers={'User-Agent': 'Mozilla/5.0'}))
    except urllib.error.HTTPError:
        return (nameSong,ID['link'])

    dowloadedFile = openLink.read()

    with open(path+'\\'+nameSong, "wb") as localFile:
        localFile.write(dowloadedFile)


def onlyPlaylist(ids,playlist):
    newIds = []
    for ID in ids:
        if playlist == ID['playlist']:
            newIds.append(ID)
    return newIds

def checkDirectory(ids,path):
    newIds = []
    oldIds = []
    filesInDirectory = os.listdir(path)
    for ID in ids:
        if creatNameFile(ID['author'],ID['nameSong']) not in filesInDirectory:
            newIds.append(ID)
        else:
            oldIds.append(ID)
    return (oldIds,newIds)

def forThread(vkRequest,ids,link,errorList,dowloadList,namespace,path):
    chunkIds = vkRequest.getChunks(ids)

    for chunk in chunkIds:
        vkRequest.getLinks(link, chunk)
        for ID in chunk:
            notDownload = dowload(ID,path)
            if notDownload: 
                errorList.append(notDownload)
            else:
                dowloadList.append(ID)
            namespace.iteration += 1
    return namespace.iteration


def main(email,password,path,link,playlist=None,thread=5):

    manager = Manager()
    namespace = manager.Namespace()

    vkRequest = SimpleRequest.VkRequest(email, password)
    ids = vkRequest.getIds(link)

    if playlist:
        ids = onlyPlaylist(ids,str(playlist))

    namespace.total = len(ids)
    oldIds,ids = checkDirectory(ids,path)
    f = open('allah2.txt','w')
    f.write(str(ids))
    f.close()

    namespace.iteration = namespace.total - len(ids)
    errorList = manager.list()
    dowloadList = manager.list(oldIds)
    partsIds = vkRequest.getParts(ids,thread)

    proc = []
    for part in partsIds:
        p = Process(target=forThread, args=(vkRequest,part,args.link,errorList,dowloadList,namespace,path))
        p.start()
        proc.append(p)

    while namespace.iteration<namespace.total:
        printProgress (namespace.iteration, namespace.total, prefix = 'Прогресс', suffix = 'Скачано',barLength = 50)
        time.sleep(1)
    printProgress (namespace.iteration, namespace.total, prefix = 'Прогресс', suffix = 'Скачано',barLength = 50)

    for p in proc:
        p.join()

    if errorList:
        print('Список не скачаных песен:')
        for error in errorList:
            print(error[0] +'-'+error[1])


if __name__ == '__main__':
    freeze_support()
    parser = argparse.ArgumentParser(description="Рюкзачек, четочки...")
    parser.add_argument('-e','--email','--login', action='store', 
        dest='email', help='Нужно ввести номер телефона или почту',required=True,type=str)
    parser.add_argument('-p','--pass','--password', action='store', 
        dest='password', help='Нужно ввести пароль',required=True,type=str)
    parser.add_argument('-l','--link', action='store', 
        dest='link', help='Ссылка на нужную страницу',required=True,type=str)
    parser.add_argument('-a','--album','--playlist', action='store', 
        dest='playlist', help='Название плейлиста в ковычках',default=None)
    parser.add_argument('-t','--thread','--process', action='store', 
        dest='thread', help='количество запускаемых потоков',default=5,type=int)
    parser.add_argument('--path', action='store', 
        dest='path', help='Путь куда сохранять',default=os.getcwd(),type=str)
    args = parser.parse_args()
    main(args.email,args.password,os.path.abspath(args.path),args.link,args.playlist,args.thread)