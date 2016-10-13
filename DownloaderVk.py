from PyQt5 import QtCore
import threading

from PyQt5.QtCore import QSize
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from html.parser import HTMLParser
import urllib
from urllib.request import Request, urlopen
import SimpleRequest
import os
import sys
import qdarkstyle
import DVk

htmlParser = HTMLParser()

class Login(QDialog):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)

        self.setWindowTitle("Авторизация")
        self.setWindowIcon(QIcon('icons/vkontakte.ico'))

        self.textName = QLineEdit(self)
        self.textPass = QLineEdit(self)
        self.textPass.setEchoMode(QLineEdit.Password)
        self.textName.setPlaceholderText("Логин")
        self.textPass.setPlaceholderText("Пароль")
        self.buttonLogin = QPushButton('Войти', self)

        self.buttonLogin.clicked.connect(self.handleLogin)
        self._authorization = None

        layout = QVBoxLayout(self)
        layout.addWidget(self.textName)
        layout.addWidget(self.textPass)
        layout.addWidget(self.buttonLogin)

    def getVkRequest(self):
        return self._authorization

    def handleLogin(self):
        try:
            self._authorization = SimpleRequest.VkRequest(self.textName.text(),self.textPass.text())
            self.accept()
        except IndexError:
            QMessageBox.warning(
                self, 'Ошибка', 'Не правильный логин, либо пароль')

class Window(QMainWindow):
    signalDownload = QtCore.pyqtSignal(tuple, name='signalDownload')

    def __init__(self,vkRequest,parent=None):
        super(Window, self).__init__(parent)
        self.setWindowIcon(QIcon('icons/vkontakte.ico'))
        self.setWindowTitle('Программа для скачивания из Vk')

        self.vkRequest = vkRequest
        self.path = os.getcwd()
        self.playlists = None
        self.thread = 5
        self.ids = None
        self.downloadIds = None
        self.errorList = []
        self.countDowload = 0

        self.grid = QGridLayout()
        widget = QWidget(self)
        widget.setLayout(self.grid)
        self.setCentralWidget(widget);

        self.editForLink = QLineEdit()
        self.editForLink.setPlaceholderText("Ссылка на страницу")
        self.grid.addWidget(self.editForLink, 0,0,1,4)

        self.comboPlayList = QComboBox(self)
        self.comboPlayList.addItem("Все")
        self.comboPlayList.activated.connect(self.changePlaylist)#activated.
        self.grid.addWidget(self.comboPlayList, 1,0,1,4)

        self.buttonSearch = QPushButton("Поиск")
        self.buttonSearch.clicked.connect(self.searchPage)
        self.grid.addWidget(self.buttonSearch, 2,3)

        self.tableWidget = QTableWidget()
        self.tableWidget.move(0,0)
        self.tableWidget.setHorizontalHeaderLabels(('Автор', 'Название', 'Плейлист'))
        self.grid.addWidget(self.tableWidget, 3,0,1,4)

        self.buttonDownload = QPushButton("Скачать")
        self.buttonDownload.clicked.connect(self.goThreads)
        self.grid.addWidget(self.buttonDownload, 4,3)

        self.progressBar = QProgressBar()
        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressBar.setGeometry(30, 40, 200, 25)
        self.resize(QSize(400,500));

        self.signalDownload.connect(self.signalHandler, QtCore.Qt.QueuedConnection)

    def signalHandler(self):
        self.countDowload += 1
        self.progressBar.setValue(round(self.countDowload/(len(self.downloadIds)+len(self.oldIds))*100))#+len(self.oldIds)
        # print("Download")

    def searchPage(self):
        try:
            self.ids = self.vkRequest.getIds(self.editForLink.text())
            self.playlists = self.vkRequest.getVkPlayLists(self.editForLink.text())
            # self.oldIds,self.ids = DVk.checkDirectory(self.ids,self.path)

            self.downloadIds = self.ids
            self.setTable(("author","nameSong","playlist"))
            self.comboPlayList.clear()
            self.comboPlayList.addItem("Все")
            for idPlaylist in self.playlists:
                if self.playlists[idPlaylist]:
                    self.comboPlayList.addItem(htmlParser.unescape(self.playlists[idPlaylist]))
        except:
            QMessageBox.warning(
                self, 'Ошибка', 'Проблема с открытием страницы')

    def goThreads(self):
        try:
            self.progressBar.setValue(0)
            self.oldIds, self.downloadIds = DVk.checkDirectory(self.downloadIds, self.path)
            self.countDowload = len(self.oldIds)

            partsIds = self.vkRequest.getParts(self.downloadIds, self.thread)
            for part in partsIds:
                th = threading.Thread(target=self.forThread, args=(self.vkRequest,part,self.editForLink.text(),self.path))
                th.start()
        except:
            QMessageBox.warning(
                self, 'Ошибка', 'Проблема с загрузкой')

    def forThread(self, vkRequest, ids, link, path):
        chunkIds = vkRequest.getChunks(ids)

        for chunk in chunkIds:
            vkRequest.getLinks(link, chunk)
            for ID in chunk:
                self.dowload(ID, path)
                self.signalDownload.emit(("ok",))

    def dowload(self, ID, path):
        nameSong = DVk.creatNameFile(ID['author'], ID['nameSong'])

        try:
            openLink = urlopen(Request(ID['link'], headers={'User-Agent': 'Mozilla/5.0'}))
        except urllib.error.HTTPError:
            return (nameSong, ID['link'])

        dowloadedFile = openLink.read()

        with open(path + '\\' + nameSong, "wb") as localFile:
            localFile.write(dowloadedFile)

    def changePlaylist(self):
        playlist = str(self.comboPlayList.currentText())
        if playlist == "Все":
            self.downloadIds = self.ids
        else:
            self.downloadIds = DVk.onlyPlaylist(self.ids,playlist)
        self.setTable(("author","nameSong","playlist"))


    def setTable(self,tupleTitles):
        self.tableWidget.setRowCount(len(self.downloadIds))
        self.tableWidget.setColumnCount(len(tupleTitles))
        self.tableWidget.setHorizontalHeaderLabels(('Автор', 'Название', 'Плейлист'))
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        i,j = 0,0
        for row in self.downloadIds:
            for column in tupleTitles:

                string = row[column]
                if not string:
                    string = ""
                else:
                    string = htmlParser.unescape(str(string))

                self.tableWidget.setItem(i,j,QTableWidgetItem(string))
                j += 1
            i += 1
            j = 0


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    login = Login()

    if login.exec_() == QDialog.Accepted:
        window = Window(login.getVkRequest())
        window.show()
        sys.exit(app.exec_())